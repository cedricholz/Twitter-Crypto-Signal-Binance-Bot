# Twitter-Signal-Cryptocurrency-Buyer


Go to your Binance account, click account, Api settings and get your API key and secret.

Create a file in the main folder called binance_secrets.json and fill it with your key and secret in the format below.

```
{
  "key": "xxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "secret": "xxxxxxxxxxxxxxxxxxxxxxxx"
}
```

Create a twitter Application here https://apps.twitter.com/app/new and get your consumer_key, consumer_secret, access_token_key, and access_token_secret.

Create a file in the main folder called twitter_secrets.json and fill it with your information in the format below.
```
{
  "consumer_key": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "consumer_secret": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "access_token_key": "xxxxxxxx-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "access_token_secret": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
}
```


Go to http://gettwitterid.com and get the twitter Id's of the people you want to follow.
Put them in twitter_user_ids_to_follow in Main.py.
