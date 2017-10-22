#!/usr/bin/python

import codecs
import datetime
import errno
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
        self.template_vars = dict()
        self.full_text = None
        self.title = None
        self.summary = None
        self.link = None
        self.full_url = None

    def read(self, config, md):
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
        input_file.close()
        root, _ = os.path.splitext(self.path)
        self.full_url = os.path.join(config["domain"], root + ".html")
    
        from jinja2 import Markup
        self.template_vars["content"] = Markup(md.reset().convert(self.full_text))
        self.template_vars["published"] = self.created.isoformat()
        self.template_vars["updated"] = self.updated.isoformat()
        self.template_vars["plain_text"] = self.full_text
        self.template_vars["create_date"] = self.created.strftime(config["date_format"])
        self.template_vars["link"] = self.link
        self.template_vars["permalink"] = self.full_url
        self.template_vars["href"] = self.link if self.link else self.full_url
        self.template_vars["title"] = self.title
        self.template_vars["title_class"] = "link" if self.link else ""
        if (self.link is not None):
            self.template_vars["summary"] = "Link To: " + self.link
        else:
            self.template_vars["summary"]  = self.summary if self.summary is not None else self.title

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
    from jinja2 import Environment, FileSystemLoader, select_autoescape
    env = Environment(
        loader=FileSystemLoader(os.path.join(config["blog"], "templates")),
        autoescape=select_autoescape(['html', 'xml']),
        trim_blocks=True,
    )
    env.globals["title"] = config["title"]
    env.globals["author"] = config["author"]
    env.globals["domain"] = config["domain"]
    env.globals["year"] = str(datetime.datetime.now().year)
    return env

def load_markdown():
    import markdown
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

def build_page(config, md, templates, page_file_name):
    engine_path = config["blog"]
    input_file = codecs.open(os.path.join(engine_path, "pages", page_file_name), mode="r", encoding="utf-8")
    root, ext = os.path.splitext(page_file_name)
    output_path = os.path.join(config["www"], root + ".html")

    text = input_file.read()
    input_file.close()

    template_vars = dict()
    template_vars["page_title"] = text.split("\n", 1)[0]
    from jinja2 import Markup
    template_vars["content"]  = Markup(md.reset().convert(text))

    template = templates.get_template("basic.html")
    html = template.render(template_vars)
    
    output_file = codecs.open(output_path, mode="w", encoding="utf-8", errors="xmlcarrefreplace")
    output_file.write(html)
    output_file.close()

def build_article(config, md, templates, article):
    engine_path = config["blog"]
    root, ext = os.path.splitext(article.path)

    output_path = os.path.join(config["www"], root + ".html")
    output_text_path = os.path.join(config["www"], root + ".text")

    makedirs(os.path.dirname(output_path))

    template_vars = dict()
    template_vars["page_title"] = article.title
    template_vars["article"] = article.template_vars

    # Plain text article
    output_text_file = codecs.open(output_text_path, mode="w", encoding="utf-8", errors="xmlcarrefreplace")
    plain_text = templates.get_template("text.html")
    text_html = plain_text.render(template_vars)
    output_text_file.write(text_html)
    output_text_file.close()

    # HTML article
    output_file = codecs.open(output_path, mode="w", encoding="utf-8", errors="xmlcarrefreplace")
    html = templates.get_template("article_standalone.html")
    final_html = html.render(template_vars)    
    output_file.write(final_html)
    output_file.close()

def build_homepage(config, md, templates, homepage_articles):
    template_vars = dict()
    template_vars["page_title"] = config["title"]
    template_vars["articles"] = homepage_articles

    template = templates.get_template("index.html")
    html = template.render(template_vars)

    output_path = os.path.join(config["www"], "index.html")
    makedirs(os.path.dirname(output_path))
    output_file = codecs.open(output_path, mode="w", encoding="utf-8", errors="xmlcarrefreplace")
    output_file.write(html)
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

    template_vars = dict()
    template_vars["page_title"] = "Archive"
    template_vars["content"] = text

    template = templates.get_template("basic.html")
    html = template.render(template_vars)

    output_path = os.path.join(config["www"], "archive.html")
    makedirs(os.path.dirname(output_path))
    output_file = codecs.open(output_path, mode="w", encoding="utf-8", errors="xmlcarrefreplace")

    output_file.write(html)
    output_file.close()

def build_feeds(config, md, templates, articles):
    atom_template = templates.get_template("atom.xml")

    template_vars = dict()
    template_vars["articles"] = articles
    template_vars["updated"] = datetime.datetime.now(pytz.utc).isoformat()
    atom_feed = atom_template.render(template_vars)
 
    atom_path = os.path.join(config["www"], "feeds", "atom.xml")
    makedirs(os.path.dirname(atom_path))

    output_file = codecs.open(atom_path, mode="w", encoding="utf-8", errors="xmlcarrefreplace")
    output_file.write(atom_feed)
    output_file.close()

def build_tweet(config, templates, article):
    tweet = templates.get_template("tweet.template").render(article.template_vars)
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
            article.read(config, md)
            build_article(config, md, templates, article)
            if len(homepage_articles) < int(config["homepage_count"]):
                homepage_articles.append(article.template_vars)
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

