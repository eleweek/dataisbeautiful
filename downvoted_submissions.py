import os
import requests
import seaborn as sns
import shelve
from operator import itemgetter
import matplotlib.image as mpimg
import praw
# Requires: https://github.com/praw-dev/praw/pull/554
# My fork already contains this change: pip install https://github.com/eleweek/praw
from praw.helpers import all_submissions

user = os.environ['REDDIT_USERNAME']
user_agent = 'Calculating % of downvoted submissions in 0.1 by /u/{}'
subreddit_stats = shelve.open("subreddit_stats.shelve", writeback=True)

highest_timestamp = 1449446399  # 06.12.2015
lowest_timestamp = highest_timestamp - 7*60*60*24 + 1


def get_default_subreddits_names():
    r = requests.get('https://www.reddit.com/subreddits/default.json?limit=100', headers={'User-Agent': user_agent})
    return [sub_info['data']['display_name'] for sub_info in r.json()['data']['children']]


def get_sub_names(sub_list):
    return [s.display_name for s in sub_list]


def get_top_subreddits():
    if '_top_defaults' in subreddit_stats and '_top_non_defaults' in subreddit_stats:
        return
    default_subreddits_names = get_default_subreddits_names()
    popular_subreddits = list(r.get_popular_subreddits(limit=1000))
    top_defaults = [s for s in popular_subreddits if s.display_name in default_subreddits_names]
    if len(top_defaults) < len(default_subreddits_names):
        for sub in set(default_subreddits_names) - set(get_sub_names(top_defaults)):
            # the top will probably be slightly incorrect
            # The 3 missing subs are philosophy, announcements and blog
            top_defaults.append(r.get_subreddit(sub))

    top_non_defaults = [s for s in popular_subreddits if s.display_name not in default_subreddits_names]
    assert len(top_defaults) == len(default_subreddits_names)
    assert len(top_non_defaults) >= 50

    subreddit_stats['_top_defaults'] = get_sub_names(top_defaults)
    subreddit_stats['_top_non_defaults'] = get_sub_names(top_non_defaults)
    subreddit_stats.sync()


def get_subreddit_stats(sublist, subreddit_stats):
    for sub in sublist:
        if str(sub) in subreddit_stats:
            continue
        downvoted_submissions = 0
        total_submissions = 0
        for submission in all_submissions(r,
                                          sub,
                                          lowest_timestamp=lowest_timestamp,
                                          highest_timestamp=highest_timestamp,
                                          verbosity=0):
            assert submission.created_utc <= highest_timestamp and submission.created_utc >= lowest_timestamp
            if submission.score <= 0:
                downvoted_submissions += 1
            total_submissions += 1
        subreddit_stats[sub] = {"downvoted_submissions": downvoted_submissions,
                                "total_submissions": total_submissions}
        subreddit_stats.sync()
        print sub, total_submissions, downvoted_submissions, downvoted_submissions / float(total_submissions) if total_submissions else 0


def sort_and_process_data(subreddit_names, subreddit_stats):
    data = []
    for sub, stats in subreddit_stats.iteritems():
        if sub not in subreddit_names:
            continue
        ds = stats['downvoted_submissions']
        ts = stats['total_submissions']
        data.append((sub, ds, ts, float(ds) / ts if ts != 0 else 0))

    return sorted(data, key=itemgetter(3, 2))


# From: http://stackoverflow.com/questions/29702424/how-to-get-matplotlib-figure-size
def get_figure_size(fig):
    bbox = fig.get_window_extent().transformed(fig.dpi_scale_trans.inverted())
    return bbox.width * fig.dpi, bbox.height * fig.dpi


def do_plot(subreddit_names, subreddit_stats, out_file, title, license_icon_filename):
    licence_icon = mpimg.imread(license_icon_filename)
    data = sort_and_process_data(subreddit_names, subreddit_stats)
    y, x = zip(*[(d[0], d[3]) for d in data])
    x = map(lambda x: x * 100, x)

    sns.set_style('whitegrid')
    print sns.plotting_context()
    sns.set(font="Bitstream Vera Sans", style='whitegrid')
    sns.set_context(rc={"figure.figsize": (16, 11), "font_scale": 1.0})
    fig = sns.plt.figure()
    ax = sns.barplot(x=x, y=y, palette="Blues")
    ax.set(xlim=(0, max(x) * 1.1))
    ax.set(xlabel="% Downvoted Submissions\n (% submissions having score <= 0)", ylabel="Subreddit name")
    ax.tick_params(labelright=True)
    rects = ax.patches

    labels = ["{} / {}".format(ds, ts) for (sub, ds, ts, dp) in data]
    for rect, label in zip(rects, labels):
        ax.text(rect.get_x() + rect.get_width() + max(x) * 0.01, rect.get_y() + rect.get_height() / 2, label, ha='left', va='center', fontsize="smaller")

    sns.plt.title(title)

    # matplotlib api is weird. I have no idea what I'm doing, but this seems to work
    width, height = get_figure_size(fig)

    # I ahve no idea why do I have to provide coordinates in different systems
    # But this set of params looks nice when I'm saving the pics
    # So fuck it, I am going to leave it like this
    # (I hope someone with good knowledge of matplotlib is willing to teach me all this stuff)

    sns.plt.figimage(licence_icon, width + 50, 10)
    sns.plt.figtext(0.99, 0.05, 'Made by\n /u/godlikesme', horizontalalignment='right')
    sns.plt.savefig(out_file, dpi=100, bbox_inches='tight')

    sns.plt.clf()

r = praw.Reddit(user_agent)
get_top_subreddits()
top_defaults = subreddit_stats['_top_defaults'][:50]
top_non_defaults = subreddit_stats['_top_non_defaults'][:50]

get_subreddit_stats(top_defaults, subreddit_stats)
get_subreddit_stats(top_non_defaults, subreddit_stats)


title_templ = "Percentage of downvoted submissions in {} (30.11.2015 - 06.12.2015)"
do_plot(top_defaults, subreddit_stats, "out_top50_defaults.png", title_templ.format("all default subreddits"), "cc-by.png")
do_plot(top_defaults[:30], subreddit_stats, "out_top30_defaults.png", title_templ.format("top30 default subreddits"), "cc-by.png")
do_plot(top_non_defaults[:50], subreddit_stats, "out_top50_non_defaults.png", title_templ.format("top50 non-default subreddits"), "cc-by.png")
