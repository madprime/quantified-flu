from datetime import datetime

from import_data.models import GarminMember
from ohapi import api

from import_data.helpers import write_jsonfile_to_tmp_dir, download_to_json

from collections import defaultdict


MAX_FILE_BYTES = 256000000 # 256 MB


def handle_dailies(json):
    user_maps = dailies_to_user_maps(json)

    for user_id in user_maps:
        # get existing files and merge
        user_map = user_maps[user_id]
        existing_user_map = get_existing_data(user_id)
        if existing_user_map:
            user_map = merge_user_maps(user_map, existing_user_map)
        upload_user_dailies(user_id, user_map)


def get_existing_data(garmin_user_id):
    oh_user = get_oh_user_from_garmin_id(garmin_user_id)
    member = api.exchange_oauth2_member(oh_user.get_access_token())
    for dfile in member['data']:
        if 'Garmin' in dfile['metadata']['tags']:
            download_url = dfile['download_url']
            return download_to_json(download_url)
    return None


def create_metadata():
    return {
        'description':
            'Garmin dailies heart rate data.',
        'tags': ['Garmin', 'heart rate'],
        'updated_at': str(datetime.utcnow()),
    }


def upload_user_dailies(garmin_user_id, user_map):

    min_date = earliest_date(user_map)
    fn = write_jsonfile_to_tmp_dir('garmin-dailies.json', user_map)
    oh_user = get_oh_user_from_garmin_id(garmin_user_id)
    api.upload_aws(fn, create_metadata(),
                                  oh_user.get_access_token(),
                                  project_member_id=oh_user.oh_id,
                                  max_bytes=MAX_FILE_BYTES)

    oh_user.garmin_member.last_updated = datetime.now()
    oh_user.garmin_member.earliest_available_data = min_date
    oh_user.garmin_member.save()


def earliest_date(user_map):
    min_ts = None
    for summary in user_map['dailies']:
        start_ts = summary['startTimeInSeconds']
        if min_ts is None or start_ts < min_ts:
            min_ts = start_ts

    return datetime.utcfromtimestamp(min_ts)


def get_oh_user_from_garmin_id(garmin_user_id):
    garmin_member = GarminMember.objects.get(userid=garmin_user_id)
    return garmin_member.member


def dailies_to_user_maps(data):
    """

    :param data:
    :return: a dictionary of garmin user id to a dictionary {"dailies": lists of summaries for said user
    """
    res = defaultdict(lambda: {"dailies": []})

    keys_to_store = ['averageHeartRateInBeatsPerMinute',
                     'maxHeartRateInBeatsPerMinute',
                     'minHeartRateInBeatsPerMinute',
                     'timeOffsetHeartRateSamples',
                     'startTimeOffsetInSeconds',
                     'summaryId',
                     'startTimeInSeconds']

    for user_dailies in data['dailies']:
        userId = user_dailies['userId']
        data_to_store = {}
        for k in keys_to_store:
            data_to_store[k] = user_dailies.get(k, None)
        res[userId]['dailies'].append(data_to_store)

    return res


def merge_user_maps(um1, um2):

    new_map = {"dailies": []}
    seen_summary_ids = set()

    for summary in um1['dailies'] + um2['dailies']:
        if summary['summaryId'] in seen_summary_ids:
            continue
        else:
            seen_summary_ids.add(summary['summaryId'])
            new_map['dailies'].append(summary)

    return new_map


def handle_backfill(garmin_member):
    pass