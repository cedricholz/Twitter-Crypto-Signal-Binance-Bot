import tweepy
from tweepy import OAuthHandler
import json

import utils


ocr = utils.get_ocr_account()

x = utils.get_image_text(ocr, "https://pbs.twimg.com/media/DR-kkH4XcAAQ-vc.jpg")

with open("twitter_secrets.json") as secrets_file:
    secrets = json.load(secrets_file)
    secrets_file.close()

consumer_key = secrets['consumer_key']
consumer_secret = secrets['consumer_secret']
access_token = secrets['access_token_key']
access_secret = secrets['access_token_secret']

auth = OAuthHandler(consumer_key, consumer_secret)
auth.set_access_token(access_token, access_secret)

api = tweepy.API(auth)

tweets = api.user_timeline(screen_name='officialmcafee',
                           count=200, include_rts=False,
                           exclude_replies=True)

for status in tweets:
    tweet_text = status._json['text']

    media = status.entities.get('media', [])
    if len(media) > 0:
        image_link = media[0]['media_url']
        tweet_text += tweet_text + '\n' + utils.get_image_text(ocr, image_link)
    print(tweet_text)

#
# print(media_files)
#
#
# print tesserocr.tesseract_version()  # print tesseract-ocr version
# print tesserocr.get_languages()  # prints tessdata path and list of available languages
#
# image = Image.open('sample.jpg')
# print tesserocr.image_to_text(image)  # print ocr text from image
# # or
# print tesserocr.file_to_text('sample.jpg')


# def download_image(url):
#     urllib.request.urlretrieve(url, "images/"+symbol+".jpg")
#
# download_image("https://pbs.twimg.com/media/DR-kkH4XcAAQ-vc.jpg",'tron')
