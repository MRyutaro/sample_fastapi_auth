from datetime import datetime, timedelta, timezone
from typing import Union
import uvicorn

from jose import jwt
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from passlib.context import CryptContext
from pydantic import BaseModel

# to get a string like this run:
# openssl rand -hex 32
SECRET_KEY = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


fake_users_db = {
    "johndoe": {
        "username": "johndoe",
        "full_name": "John Doe",
        "email": "johndoe@example.com",
        "hashed_password": "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",
        "disabled": False,
    }
}


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Union[str, None] = None


class User(BaseModel):
    username: str
    email: Union[str, None] = None
    full_name: Union[str, None] = None
    disabled: Union[bool, None] = None


class UserInDB(User):
    hashed_password: str


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

app = FastAPI()


# plain_passwordとhashed_passwordが一致するか確認する
# plain_passwordはユーザから入力されたパスワード、hashed_passwordはDBに保存されているハッシュ化されたパスワード
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


# パスワードをハッシュ化する
def get_password_hash(password):
    return pwd_context.hash(password)


# DBからユーザー情報を取得する
def get_user(db, username: str):
    if username in db:
        user_dict = db[username]
        return UserInDB(**user_dict)


# ユーザー認証を行う
def authenticate_user(fake_db, username: str, password: str):
    user = get_user(fake_db, username)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user


# /tokenエンドポイントにアクセスしたときにこの関数が呼び出されて、アクセストークンを生成する
def create_access_token(data: dict, expires_delta: Union[timedelta, None] = None):
    to_encode = data.copy()
    # もし有効期限が設定されていれば、有効期限を設定する
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    # 有効期限が設定されていない場合は、15分後に有効期限を設定する
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    # トークン = { "sub": "johndoe", "exp": 1618312741.0 } のようなデータをエンコードしたもの
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer error='invalid token'"}
    )
    try:
        # トークンをデコードすることで、{ "sub": "johndoe" } のようなデータを取得できる
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        # create_access_tokenで設定したdataの内容を取得
        username: str = payload.get("sub")
        exp: float = payload.get("exp")
        print(f"get_current_user: {username=}, {exp=}")
        token_data = TokenData(username=username)
    except Exception:
        raise credentials_exception
    user = get_user(fake_users_db, username=token_data.username)
    if user is None:
        raise credentials_exception
    return user


# ユーザーが有効かどうかを確認する
# disabledはユーザーが無効かどうかを示すフラグ
# ユーザが無効というのは、ユーザーが削除されたか、アカウントがロックされたか、何らかの理由でアクセスが制限されている状態を指す
async def get_current_active_user(current_user: User = Depends(get_current_user)):
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


# もしパスワードがあっていれば、アクセストークンを返す
# アクセストークンはCookieやHeaderに設定されるもので以下の形式で返される
# {
#   "access_token": "string",
#   "token_type": "string"
# }
@app.post("/token")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()) -> Token:
    user = authenticate_user(
        fake_users_db,
        form_data.username,
        form_data.password
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={
                "WWW-Authenticate": "Bearer error='incorrect username or password'"}
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={
            "sub": user.username
        },
        expires_delta=access_token_expires
    )
    # Reactとかで使う場合はレスポンスをlocalStorage, sessionStorage, cookieのどれかに保存しておくみたいな処理をすれば良い
    return Token(access_token=access_token, token_type="bearer")


# ユーザー情報を取得する
# フローは以下の通り
# 1. ユーザがこのエンドポイントにアクセスする
# 2. get_current_active_user関数が呼び出される
# 3. get_current_user関数が呼び出される
# 4. トークンがデコードされ、ユーザー名が取得される
# ユーザから渡されるデータは以下のような形式
# curl -X 'GET' \
#   'http://127.0.0.1:8000/users/me/' \
#   -H 'accept: application/json' \
#   -H 'Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJqb2huZG9lIiwiZXhwIjoxNzIyOTU0OTU4fQ.X9-kpGVwnHi4E6-qEhlv9ST26sfBzxv8P9xVc0fMTAs'
# つまり、React側から送るときには以下のようにすればいい
# fetch('http://localhost:8000/users/me/', {
#   method: 'GET',
#   headers: {
#     'Authorization': `Bearer ${token}`
#   }
#
@app.get("/users/me/", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    return current_user


@app.get("/users/me/items/")
async def read_own_items(current_user: User = Depends(get_current_active_user)):
    return [
        {
            "item_id": "Foo",
            "owner": current_user.username
        }
    ]


if __name__ == "__main__":
    uvicorn.run("main:app", port=8000, reload=True)
