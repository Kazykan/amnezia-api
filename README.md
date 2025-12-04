Get token

```
POST http://localhost:8000/api/auth/login
Content-Type: application/json

{
  "username": "admin",
  "password": "1234"
}
```

get client

```
curl http://localhost:8000/api/wg/clients -H "Authorization: Bearer <TOKEN>" | jq

```
