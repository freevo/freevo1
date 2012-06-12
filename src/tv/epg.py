__author__ = 'adam'

import config
import kaa.epg
from kaa.epg.util import EPGError
import os
from tv.epg_types import DbTvProgram, TvChannel


#Temporary load local epg, this needs to be changed to use a server
if config.HELPER_APP in ['recordserver', 'tv_grab', 'cache', 'tvmanager']:
    EPG_LOCAL = True
    kaa.epg.load(os.path.join(config.FREEVO_CACHEDIR, 'epg.db'))
    if config.HELPER_APP in ['recordserver', 'tvmanager']:
        print 'Starting EPG server'
        kaa.epg.listen(('', 10000), config.RECORDSERVER_SECRET)
else:
    print 'Connecting to EPG server'
    kaa.epg.connect((config.RECORDSERVER_IP, 10000), config.RECORDSERVER_SECRET)
    EPG_LOCAL = False

channels = []
channels_by_id = {}
channels_by_tuner_id = {}
channels_by_display_name = {}

for channel_details in config.TV_CHANNELS:
    channel = TvChannel(channel_details[0], channel_details[1], channel_details[2])
    if len(channel_details) > 3 and len(channel_details[3:4]) == 3:
        for (days, start_time, stop_time) in channel_details[3:4]:
            channel.times.append((days, int(start_time), int(stop_time)))

    channels.append(channel)
    channels_by_id[channel_details[0]] = channel
    channels_by_tuner_id[channel.tunerid] = channel
    channels_by_display_name[channel.displayname] = channel


def get_grid(start, stop, channels):
    import tv.record_client

    rpc_channel = tv.record_client.RecordClient().channel
    if rpc_channel.status != kaa.rpc.CONNECTED:
        return []
    channel_ids = []
    for channel in channels:
        if isinstance(channel, TvChannel):
            channel = channel.id
        channel_ids.append(channel)

    return rpc_channel.rpc('getGrid', start, stop, channel_ids).wait()


def get_programs(start=0, stop=0, channel_id=None):
    kwargs = { 'time': (start,stop)}

    if channel_id is not None:
        if isinstance(channel_id, (list,tuple)):
            selected_channels = []
            channels = []
            for channel in channel_id:
                if isinstance(channel, TvChannel):
                    channel = channel.id
                channels.append(kaa.epg.get_channel_by_tuner_id(channel))
                selected_channels.append(channel)
            kwargs['channel'] = channels
        else:
            if isinstance(channel_id, TvChannel):
                channel_id = channel_id.id
            kwargs['channel'] = kaa.epg.get_channel_by_tuner_id(channel_id)
            selected_channels = [channel_id]
    else:
        selected_channels = None

    try:
        progs = kaa.epg.search(**kwargs).wait()
    except EPGError:
        progs = []

    channel_dict = {}
    for prog in progs:
        tuner_id = prog.channel.tuner_id[0]
        tv_prog = DbTvProgram(prog)
        channel_dict.setdefault(tuner_id, []).append(tv_prog)
    channels = []

    for channel_details in config.TV_CHANNELS:
        if selected_channels is None or channel_details[0] in selected_channels:
            channel = TvChannel(channel_details[0], channel_details[1], channel_details[2])
            if channel_details[0] in channel_dict:
                channel.programs = channel_dict[channel_details[0]]
            channels.append(channel)

    return channels

def search(channel_id=None, time=None, keyword=None, title=None, category=None):
    kwargs = {}

    if time is not None:
        kwargs['time'] = time

    if channel_id is not None:
        kwargs['channel'] = kaa.epg.get_channel_by_tuner_id(channel_id)

    if title is not None:
        kwargs['title'] = unicode(title)

    if keyword is not None:
        kwargs['keywords'] = unicode(keyword)

    if category is not None:
        kwargs['genres'] = category

    progs = kaa.epg.search(**kwargs).wait()
    programs = [DbTvProgram(p) for p in progs]

    return programs

def get_categories():
    return [genre for genre,_ in kaa.epg.get_genres().wait()]

def update(filename=None):
    if not EPG_LOCAL:
        # When the epg is remote there is nothing to do.
        return
    kaa.epg.update.config.sources = 'xmltv'
    if filename is None:
        kaa.epg.update.config.xmltv.data_file = config.XMLTV_FILE
    else:
        kaa.epg.update.config.xmltv.data_file = filename
    kaa.epg.update().wait()