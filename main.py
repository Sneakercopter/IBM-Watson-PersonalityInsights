from __future__ import print_function
import tweepy
import time
import os
import json
from watson_developer_cloud import PersonalityInsightsV3

class Interviewer:

    def __init__(self):
        self.settings = self.loadSettings()
        if self.settings == None:
            # No settings no deal
            exit(0)
        self.handle = self.settings["twitter_handle"]
        self.access_key = self.settings["twitter_access_key"]
        self.access_secret = self.settings["twitter_access_secret"]
        self.consumer_key = self.settings["twitter_consumer_key"]
        self.consumer_secret = self.settings["twitter_consumer_secret"]
        self.pi_url = self.settings["watson_pi_url"]
        self.pi_username = self.settings["watson_pi_username"]
        self.pi_password = self.settings["watson_pi_password"]
        self.auth = tweepy.OAuthHandler(self.consumer_key, self.consumer_secret)
        self.auth.set_access_token(self.access_key, self.access_secret)
        self.twitter_api = tweepy.API(self.auth)

    def loadSettings(self):
        if(os.path.exists("settings.json")):
            with open("settings.json", "r") as settings:
                try:
                    jsonSettings = json.loads(settings.read())
                    # We need to verify all needed fields are present
                    requiredKeys = ["twitter_handle", "twitter_access_key", "twitter_access_secret", "twitter_consumer_key", "twitter_consumer_secret", "watson_pi_url", "watson_pi_username", "watson_pi_password"]
                    for key in requiredKeys:
                        if not key in jsonSettings.keys():
                            print("Settings is missing key: \"%s" % key + "\". Please add it in to continue!")
                            return None
                    return jsonSettings
                except Exception as e:
                    print("Could not read settings file, make sure it is formatted correctly!")
                    return None
        else:
            print("Could not find settings.json, cannot continue!")
            return None

    def pullTweets(self):
        max_id = None
        statuses = []

        for x in range(0, 16):  # Pulls max number of tweets from an account
            if x == 0:
                statuses_portion = self.twitter_api.user_timeline(screen_name=self.handle,
                                                             count=200,
                                                             include_rts=False)
                status_count = len(statuses_portion)
                # get id of last tweet and bump below for next tweet set
                max_id = statuses_portion[status_count - 1].id - 1
            else:
                statuses_portion = self.twitter_api.user_timeline(screen_name=self.handle,
                                                             count=200,
                                                             max_id=max_id,
                                                             include_rts=False)
                status_count = len(statuses_portion)
                try:
                    # get id of last tweet and bump below for next tweet set
                    max_id = statuses_portion[status_count - 1].id - 1
                except Exception:
                    pass
            for status in statuses_portion:
                statuses.append(status)
        print('Number of Tweets user have: %s' % str(len(statuses)))
        return statuses

    def convert_status_to_pi_content_item(self, s):
        return {
            'userid': str(s.user.id),
            'id': str(s.id),
            'sourceid': 'python-twitter',
            'contenttype': 'text/plain',
            'language': s.lang,
            'content': s.text,
            'created': str(int(time.time())),
            'reply': (s.in_reply_to_status_id is None),
            'forward': False
        }

    def printFormatted(self, jsonData):
        interested_traits = ["needs", "consumption_preferences", "values", "behavior", "personality"]

        for trait in interested_traits:
            print("Trait: " + trait)
            trait_data = jsonData[trait]
            for extra_data in trait_data:
                if trait == "needs":
                    print("\t %s" % extra_data["name"] + " -> %s" % extra_data["percentile"])
                elif trait == "consumption_preferences":
                    print("\t Consumption Preference: %s" % extra_data["consumption_preference_category_id"])
                    for pref in extra_data["consumption_preferences"]:
                        print("\t\t %s" % pref["name"] + " -> %s" % pref["score"])
                elif trait == "values":
                    print("\t %s" % extra_data["name"] + " -> %s" % extra_data["percentile"])
                elif trait == "behavior":
                    print("\t %s" % extra_data["trait_id"] + " -> %s" % extra_data["percentage"])
                elif trait == "personality":
                    print("\t %s" % extra_data["name"] + " -> %s" % extra_data["percentile"])
                else:
                    print("\t %s" % extra_data)

    def watsonSubmission(self, statuses):
        pi_content_items_array = map(self.convert_status_to_pi_content_item, statuses)
        pi_content_items = {'contentItems': pi_content_items_array}

        personality_insights = PersonalityInsightsV3(
            version='2017-10-13',
            username=self.pi_username,
            password=self.pi_password,
            url=self.pi_url
        )

        profile = personality_insights.profile(pi_content_items, content_type='application/json',
                                               consumption_preferences=True, raw_scores=True).get_result()
        self.printFormatted(profile)

i = Interviewer()
i.watsonSubmission(i.pullTweets())