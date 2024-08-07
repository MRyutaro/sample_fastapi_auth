# sample_fastapi_auth
## 必要なライブラリのインストール

- `pip install fastapi`
- `pip install python-jose[cryptography]`
- `pip install passlib[bcrypt]`

## メモ

JWTは、クライアント側に渡すデータ（アクセストークン）の中にユーザ情報を持たせるもの。ユーザ情報を入れたjsonをエンコードしたもの。

JWTの文字列は以下のように構成されている。（[参考](https://qiita.com/nokonoko_1203/items/966dc356c3763136c368))

```
ヘッダーをエンコードした文字列ードをエンコードした文字列.署名をエンコードした文字列
```

アクセストークンを保存する場所の選択肢は以下の通り

| 手法 | 説明 |
| --- | --- |
| localStorage | XSS攻撃に合う可能性があるためここに保存してはいけない。 |
| sessionStorage | XSS攻撃に合う可能性があるためここに保存してはいけない。タブを閉じると消える。 |
| cookie | httpOnly Cookieに保存する。httpOnly CokkieだとJSからCokkieを参照できなくなるらしい。CSRF攻撃対策をする必要あり。 |

けどセキュリティリスクがあるとのこと。

- [nyandora(nyandora). JWTは使うべきではない　〜 SPAにおける本当にセキュアな認証方式 〜. Qiita.](https://qiita.com/nyandora/items/8174891f52ec0ea15bc1)
- [Shota Nukumizu. JWT認証のベストプラクティス 5選. Zenn.](https://zenn.dev/nameless_sn/articles/the_best_practice_of_jwt)

長い期間保持したいデータを管理するのにJWTを使うな。JWTトークンとsessionを組み合わせて使え。

- [Stop using JWT for sessions. June 19, 2016. ](http://cryto.net/~joepie91/blog/2016/06/13/stop-using-jwt-for-sessions/)

一方で、クライアント側に渡すデータにユーザ情報を持たせず、サーバ側でユーザ情報を保持しておく方法もある。これはセッションidを使う方法。

![https://zenn.dev/swy/articles/0e8de582f4e7f3](/docs/images/image.png)

認証についての参考記事

- [Hiro-mi(ひ ろ). SPAのログイン認証のベストプラクティスがわからなかったのでわりと網羅的に研究してみた〜JWT or Session どっち？〜. Qiita.](https://qiita.com/Hiro-mi/items/18e00060a0f8654f49d6)