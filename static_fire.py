#!/usr/bin/python

import codecs
import datetime
import errno
import markdown
import os
import pytz
import shutil
import sys
import time

import dateutil.parser
from distutils.dir_util import copy_tree
from operator import itemgetter

class Article:
    def __init__(self, path, created, updated, is_new):
        self.path = path
        self.created = created
        self.updated = updated
        self.is_new = is_new

        # Filled in when read() is called
        self.full_text = None
        self.title = None
        self.summary = None
        self.link = None
        self.full_url = None

    def read(self, config):
        input_file = codecs.open(os.path.join(config["blog"], self.path), mode="r", encoding="utf-8")

        line = input_file.readline().rstrip()
        while(line != "end_header"):
            key, remainder = line.split(" ", 1)
            if (key == "title"):
                self.title = remainder
            elif (key == "summary"):
                self.summary = remainder
            elif (key == "link"):
                self.link = remainder
            else:
                print("Unrecognized metadata: " + line)
            line = input_file.readline().rstrip()

        self.full_text = input_file.read()
        root, _ = os.path.splitext(self.path)
        self.full_url = os.path.join(config["domain"], root + ".html")

        input_file.close()

    def __repr__(self):
        return self.path + " created: " + unicode(self.created) + " updated: " + unicode(self.updated)

def load_config():
    print("Config")
    config = {}
    config["blog"] = os.getcwd()
    print("Assinging 'blog' as '" + config["blog"] + "'")
    with open(os.path.join(config["blog"], "config"), "r") as config_f:
        for line in config_f:
            line = line.split("#")[0]
            if not line or not line.rstrip():
                continue
            key, value = line.split(" ", 1)
            value = value.rstrip()
            if "secret" not in key:
                print("Assinging '" + key + "' as '" + value + "'")
            else:
                print("Assinging '" + key + "' as '" + len(value)*"*" + "'")
            config[key] = value
    return config

def load_templates(config):
    print("Templates")
    templates = {}
    templates_path = os.path.join(config["blog"], "templates")
    for filename in os.listdir(templates_path):
        if filename.endswith(".template"):
            print(filename)
            template_file = codecs.open(os.path.join(templates_path, filename), mode="r", encoding="utf-8")
            template_text = template_file.read()
            basename = os.path.basename(filename)
            name, _ = os.path.splitext(basename)
            templates[name] = template_text
            template_file.close()
    return templates

def load_markdown():
    extensions = ["markdown.extensions.footnotes", "markdown.extensions.smarty"]
    extension_configs = {
        "markdown.extensions.footnotes": { "UNIQUE_IDS": True }
    }
    md = markdown.Markdown(extensions=extensions, extension_configs=extension_configs)
    return md

def get_twitter_api(config):
    keys = ("twtr_consumer_key", "twtr_consumer_secret", "twtr_access_token", "twtr_access_token_secret")
    if not all (k in config for k in keys):
        return None
    import tweepy
    auth = tweepy.OAuthHandler(config["twtr_consumer_key"], config["twtr_consumer_secret"])
    auth.set_access_token(config["twtr_access_token"], config["twtr_access_token_secret"])
    return tweepy.API(auth)

def makedirs(path):
    try:
        os.makedirs(path)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise

def format_copyright(config):
    return "Copyright " + u"\u00A9" + " " + str(datetime.datetime.now().year) + " " + config["author"]

def build_page(config, md, templates, page_file_name):
    engine_path = config["blog"]
    input_file = codecs.open(os.path.join(engine_path, "pages", page_file_name), mode="r", encoding="utf-8")
    root, ext = os.path.splitext(page_file_name)
    output_path = os.path.join(config["www"], root + ".html")
    output_file = codecs.open(output_path, mode="w", encoding="utf-8", errors="xmlcarrefreplace")

    text = input_file.read()
    html = md.reset().convert(text)

    html = templates["base"].replace("%BODY%", html)
    html = html.replace("%COPYRIGHT%", format_copyright(config))
    html = html.replace("%TWITTER_CARD%", "")
    html = html.replace("%FB_OG%", "")
    title = text.split("\n", 1)[0]
    html = html.replace("%TITLE%", title)
    
    output_file.write(html)

    input_file.close()
    output_file.close()

def build_article_html(config, md, templates, article):
    html = md.reset().convert(article.full_text)
    date = article.created.strftime(config["date_format"])
    title_href = article.link if article.link else article.full_url
    title_class = "link" if article.link else ""

    template_text = templates["article"]
    template_text = template_text.replace("%TITLE_CLASS%", title_class)
    template_text = template_text.replace("%TITLE_HREF%", title_href)
    template_text = template_text.replace("%TITLE%", article.title)
    template_text = template_text.replace("%PERMA_HREF%", article.full_url)
    template_text = template_text.replace("%DATE%", date)
    template_text = template_text.replace("%ARTICLE%", html)

    return template_text

def build_article(config, md, templates, article):
    engine_path = config["blog"]
    root, ext = os.path.splitext(article.path)

    output_path = os.path.join(config["www"], root + ".html")
    output_text_path = os.path.join(config["www"], root + ".text")

    makedirs(os.path.dirname(output_path))
    output_file = codecs.open(output_path, mode="w", encoding="utf-8", errors="xmlcarrefreplace")
    output_text_file = codecs.open(output_text_path, mode="w", encoding="utf-8", errors="xmlcarrefreplace")

    # Plain text stuff
    plain_text = article.title + "\n"
    plain_text += "="*len(article.title) + "\n\n"
    plain_text += "    By " + config["author"] + "\n"
    date = article.created.strftime(config["date_format"])
    plain_text += "    " + date + "\n"
    if (article.link is not None):
        plain_text += "    Link: " + article.link + "\n"
    plain_text += "    " + article.full_url + "\n\n"
    plain_text += article.full_text
    
    text_template_text = templates["text"]
    text_html = text_template_text.replace("%BODY%", plain_text)

    # Header and FB and Twitter stuff
    base_html = templates["base"]
    base_html = base_html.replace("%TITLE%", article.title)

    summary = None
    if (article.link is not None):
        summary = "Link To: " + article.link
    if (summary is None):
        summary = article.summary if article.summary is not None else article.title

    twitter_card_text = templates["twitter_card"]
    twitter_card_text = twitter_card_text.replace("%TITLE%", article.title)
    twitter_card_text = twitter_card_text.replace("%SUMMARY%", summary)

    fb_og_text = templates["fb_og"]
    fb_og_text = fb_og_text.replace("%TITLE%", article.title)
    fb_og_text = fb_og_text.replace("%URL%", article.full_url)
    fb_og_text = fb_og_text.replace("%SUMMARY%", summary)

    base_html = base_html.replace("%TWITTER_CARD%", twitter_card_text)
    base_html = base_html.replace("%FB_OG%", fb_og_text)
    base_html = base_html.replace("%COPYRIGHT%", format_copyright(config))
    
    # Fill in article
    article_html = build_article_html(config, md, templates, article)
    final_html = base_html.replace("%BODY%", article_html)

    output_file.write(final_html)
    output_text_file.write(text_html)

    output_file.close()
    output_text_file.close()

    return article

def build_homepage(config, md, templates, homepage_articles):
    engine_path = config["blog"]
    output_path = os.path.join(config["www"], "index.html")
    makedirs(os.path.dirname(output_path))
    output_file = codecs.open(output_path, mode="w", encoding="utf-8", errors="xmlcarrefreplace")

    base_html = templates["base"]
    base_html = base_html.replace("%TITLE%", config["title"])
    articles = ""
    for article in homepage_articles:
        article_html = build_article_html(config, md, templates, article)
        articles += article_html

    base_html = base_html.replace("%COPYRIGHT%", format_copyright(config))
    base_html = base_html.replace("%TWITTER_CARD%", "")
    base_html = base_html.replace("%FB_OG%", "")
    base_html = base_html.replace("%BODY%", articles)

    output_file.write(base_html)
    output_file.close()

def build_archive(config, md, templates, articles):
    import calendar

    text = ""
    year = None
    month = None
    for article in articles:
        if (year != article.created.year):
            year = article.created.year
            text += '<h1>' + str(year) + '</h1>\n'
        if (month != article.created.month):
            month = article.created.month
            text += '<h1>' + calendar.month_name[month] + '</h1>\n'

        text += '<a href="' + article.full_url + '">' + article.title + '</a><br/>'

    base_html = templates["base"].replace("%BODY%", text)
    base_html = base_html.replace("%TITLE%", "Archive")
    base_html = base_html.replace("%COPYRIGHT%", format_copyright(config))
    base_html = base_html.replace("%TWITTER_CARD%", "")
    base_html = base_html.replace("%FB_OG%", "")

    engine_path = config["blog"]
    output_path = os.path.join(config["www"], "archive.html")
    makedirs(os.path.dirname(output_path))
    output_file = codecs.open(output_path, mode="w", encoding="utf-8", errors="xmlcarrefreplace")

    output_file.write(base_html)
    output_file.close()

def build_feeds(config, md, templates, articles):
    atom_feed = templates["atom"]
    atom_feed = atom_feed.replace("%ID%", os.path.join(config["domain"], "feeds", "atom.xml"))
    atom_feed = atom_feed.replace("%TITLE%", config["title"])
    atom_feed = atom_feed.replace("%SUBTITLE%", "By " + config["author"])
    atom_feed = atom_feed.replace("%LINK_ALTERNATE%", config["domain"])
    atom_feed = atom_feed.replace("%LINK_SELF%", os.path.join(config["domain"], "feeds", "atom.xml"))
    atom_feed = atom_feed.replace("%RIGHTS%", format_copyright(config))
    atom_feed = atom_feed.replace("%UPDATED%", datetime.datetime.now(pytz.utc).isoformat())
    
    engine_path = config["blog"]
    entries = ""
    for article in articles:
        entry = templates["atom_entry"]
        entry = entry.replace("%ID%", article.full_url)
        entry = entry.replace("%TITLE%", article.title)
        if (article.link is None):
            entry = entry.replace("%LINK_ALTERNATE%", article.full_url) 
            entry = entry.replace("%LINK_RELATED%", "") 
        else:
            entry = entry.replace("%LINK_ALTERNATE%", article.link) 
            entry = entry.replace("%LINK_RELATED%", '<link href="' + article.full_url + '" rel="related"/>') 
        entry = entry.replace("%PUBLISHED%", article.created.isoformat())
        entry = entry.replace("%UPDATED%", article.updated.isoformat())
        entry = entry.replace("%AUTHOR_NAME%", config["author"])
        entry = entry.replace("%AUTHOR_URI%", config["domain"])

        article_html = md.reset().convert(article.full_text)
        entry = entry.replace("%CONTENT%", article_html)
        entries += entry

    atom_feed = atom_feed.replace("%ENTRIES%", entries)
 
    atom_path = os.path.join(config["www"], "feeds", "atom.xml")
    makedirs(os.path.dirname(atom_path))

    output_file = codecs.open(atom_path, mode="w", encoding="utf-8", errors="xmlcarrefreplace")
    output_file.write(atom_feed)
    output_file.close()

def build_tweet(config, templates, article):
    tweet = templates["tweet"]
    tweet = tweet.replace("%TITLE%", article.title)
    tweet = tweet.replace("%URL%", article.full_url)
    print("Tweet: " + tweet)           
    return tweet

def query_git_articles(config):
    from git import Repo
    print("Git")
    repo = Repo(config["blog"])
    git = repo.git

    articles = list()
    article_files = git.ls_files("articles/*.text").split("\n")
    for article_file in article_files:
        if not os.path.isfile(article_file):
            continue
        article_revs = git.rev_list("HEAD", article_file).split("\n")
        first_rev = article_revs[-1]
        last_rev = article_revs[0]
        first_timestamp = git.show("-s", "--format=\"%aI\"", first_rev).strip("\"")
        last_timestamp = git.show("-s", "--format=\"%aI\"", last_rev).strip("\"")

        created = dateutil.parser.parse(first_timestamp)
        updated = dateutil.parser.parse(last_timestamp)

        head_rev = git.show("-s", "HEAD", "--format=\"%H\"").strip("\"")
        is_new = (head_rev == first_rev)

        a = Article(article_file, created, updated, is_new)
        articles.append(a)

    articles.sort(key=lambda a: a.created, reverse=True)
    return articles
    
def main(argv):
    config = load_config()
    os.environ["GIT_DIR"] = os.path.join(config["blog"], ".git")
    templates = load_templates(config)
    md = load_markdown()

    website_dir = config["www"]

    articles = query_git_articles(config)

    homepage_articles = list()

    copy_tree(os.path.join(config["blog"], "www"), website_dir)

    for article in articles:
        if article.path.endswith(".text"):
            print(article)
            article.read(config)
            article = build_article(config, md, templates, article)
            if len(homepage_articles) < int(config["homepage_count"]):
                homepage_articles.append(article)
            if (article.is_new):
                twitter = get_twitter_api(config)
                if (twitter):
                    tweet = build_tweet(config, templates, article)
                    status = twitter.update_status(status=tweet)

    build_homepage(config, md, templates, homepage_articles)
    build_feeds(config, md, templates, homepage_articles)
    build_archive(config, md, templates, articles)

    # Extra pages
    for filename in os.listdir(os.path.join(config["blog"], "pages")):
        if filename.endswith(".text"): 
            build_page(config, md, templates, filename)

if __name__ == "__main__":
    main(sys.argv)

