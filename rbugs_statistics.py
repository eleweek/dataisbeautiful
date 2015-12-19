import os
from datetime import datetime
from datetime import date
from collections import defaultdict
import json

import praw
from praw.helpers import submissions_between

import seaborn as sns
import matplotlib.patches as mpatches


def get_flair_stats():
    user = os.environ['REDDIT_USERNAME']
    user_agent = 'Calculating ignored bugs by {}'.format(user)

    r = praw.Reddit(user_agent)
    flair_stats = defaultdict(lambda: defaultdict(lambda: 0))

    for s in submissions_between(r, 'bugs', lowest_timestamp=1400000000):
        created = datetime.utcfromtimestamp(s.created_utc)
        month = (created.year, created.month)
        # They started to add flairs since Janury, 2015
        if month < (2015, 2):
            break
        # Current month has incomplete data
        if month == (date.today().year, date.today().month):
            continue
        # Submissions without flairs seems to be mainly duplicate submissions removed by mods
        # They are not viewable in the interface, so we aren't counting them
        if not s.link_flair_text:
            print "IGNORING POST WITHOUT A FLAIR", s.permalink, s.title
            continue
        flair_stats[month][s.link_flair_text] += 1

    return flair_stats


def convert_month_keys_to_strings(flair_stats):
    return {("{}.{}" if m > 9 else "{}.0{}").format(y, m): v
            for ((y, m), v) in flair_stats.iteritems()}


def do_plot(flair_stats, filename):
    months = []
    new_flaired = []
    total = []

    for month, month_stats in sorted(flair_stats.items()):
        total.append(sum(month_stats.values()))
        new_flaired.append(month_stats['new'])
        months.append(month)

    sns.set_style('whitegrid')

    total_plot_color = sns.xkcd_rgb["denim blue"]
    ignored_plot_color = sns.xkcd_rgb["orange red"]

    total_plot = sns.pointplot(x=months, y=total, color=total_plot_color)
    sns.pointplot(x=months, y=new_flaired, color=ignored_plot_color)

    total_patch = mpatches.Patch(color=total_plot_color)
    ignored_patch = mpatches.Patch(color=ignored_plot_color)

    total_plot.set(ylabel="Number of bugreports", xlabel="Month")
    total_plot.set_title('/r/bugs statistics by month:\nReddit admins consistently ignore half of bugreports', y=1.02)
    sns.plt.legend([total_patch, ignored_patch], ['Total number of bugreports',
                                                  'Number of ignored bugreports (submissions with "new" flair)'],
                   loc="lower left")

    sns.plt.savefig(filename)

if not os.path.exists("rbugs_flair_stats.json"):
    flair_stats = convert_month_keys_to_strings(get_flair_stats())
    with open("rbugs_flair_stats.json", "w") as flair_stats_file:
        json.dump(flair_stats, flair_stats_file)
else:
    with open("rbugs_flair_stats.json") as flair_stats_file:
        flair_stats = json.load(flair_stats_file)

do_plot(flair_stats, "rbugs_statistics.png")
