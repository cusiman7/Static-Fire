Static Fire
===========

Static Fire is an engine for creating static websites, primarily blogs.
Instead of a standard database Static Fire uses Git as its primary data store.
Static Fire was built by [@RobertCusimano](https://twitter.com/RobertCusimano) and powers [ShadedTriangle](https://ShadedTriangle.com).

## Features
+ Markdown articles
+ [Jinja2](http://jinja.pocoo.org/docs/2.9/) templating
+ Linked list style articles
+ Git based datastore
    + No database management
    + Publish from your phone with any old Git client (I like [Working Copy](https://workingcopyapp.com/))
+ Atom feed generation
+ Tweet new articles
+ Twitter Cards and Facebook Open Graph meta tags built in
+ Plain text articles
+ Cloudflare API integration to purge static files from Cloudflare's cache

## Installation (Local)
    # Git clone then...
    pip install -r requirements.txt

## Installation (Webserver)
    # Git clone or git push to webserver. You want a normal repository not a bare repository. Then...
    pip install -r requirements.txt
    cp post-receive .git/hooks/ # Will run static_fire.py after a git push is received
    git config --local receive.denyCurrentBranch updateInstead # Allows a git push to update the local working copy

## Usage
    ./static_fire.py

All the action takes place in static\_fire.py.
You can run it right now and it should generate an example website for you in "/usr/local/var/www".
Place new plain text Markdown files ending with ".text" in the articles folder, commit them to git, and the next time Static Fire runs it will generate html pages for them.

### Article Header
Articles are standard Markdown files except for a small header for metadata. Metadata lines are a simple key and value that splits on the first space. A sinlge line of "end_header" marks the end of the header. An example header might look like:

    title Markdown Syntax
    summary A link to DaringFireball's Markdown Syntax page.
    link https://daringfireball.net/projects/markdown/syntax
    end_header

+ **title**
    
    *Required*. The title of the article used for page titles, headers, tweets, feeds, and the archive.

+ **summary**

    *Optional*. The summary of the article is used for tweets and feeds and is completely optional. If missing summaries will be populated from the title.

+ **link**

    *Optional*. If your article is primarily a link to some other content this will make the header of the article be a link. This will also populate the feed entry with an "alternate" of the link and a "related" of the url of the article instead of the usual which is an "alternate" to the article itself.

### Config
Static Fire looks for a file called "config" next to it. Config lines are simple key values that split on the first space.
An example config looks like:

    # Example Config
    # Don't commit this file. It will contain OAuth secrets
    www /usr/local/var/www # Website dir
    domain http://localhost:8080
    title Static Fire
    author Rob Cusimano
    date_format %B %d, %Y # strftime behavior
    homepage_count 50 # Count of articles on homepage and in Atom feed

#### Required Config Keys
+ **www**

    *String*. The location your website is served from.

+ **domain** 

    *String*. Your website's domain. For example: https://shadedtriangle.com

+ **title** 

    *String*. Your website's title for its homepage and feeds.

+ **author** 

    *String*. Your name here.

+ **date\_format** 

    *String*. A nice format to print dates for your articles in Python's strftime format.

+ **homepage\_count** 

    *Int*. The number of most-recent articles to appear on the homepage and feeds.

#### Optional Config Keys
"twtr\*" keys are used collectively for auto tweeting new articles. No keys, no tweets.

+ **twtr\_access\_token** 

    *String*

+ **twtr\_access\_token\_secret** 

    *String*

+ **twtr\_consumer\_key** 
    
    *String*

+ **twtr\_consumer\_secret** 

    *String*

"cloudflare\*" keys are used to purge static content from Cloudflare's cache when that content changes.

+ **cloudflare\_email**

    *String*

+ **cloudflare\_zone\_id**

    *String*

+ **cloudflare\_secret\_api\_key**

    *String*

### Static Fire's Actions
static\_fire.py performs the following actions:

1. Load config and templates
2. Gather articles from Git
3. Copy the contents of www/ to config's "www" 
    + Useful for css, images, etc.
4. Build each article page
    + If it's a new article, tweet it
5. Build homepage
6. Build feeds
7. Build archive page
8. Build additonal pages
9. Purge files from Cloudflare's cache

### Additional Pages
Markdown files ending with ".text" in the "pages/" directory will be compiled into .html files and placed at the root of your website. This is useful for about pages or error pages like 404, 503 etc. The first line of the file should be the title of the page followed by the second line of "==" for Markdown.

### Post Receive Git Hook
post-receive is a simple git hook to execute static\_fire.py after a git push is received.
post-receive should be installed in ".git/hooks/" on your webserver to enable site re-building when you push new articles.

### Auto Tweet
Static Fire will tweet articles if the commit they were authored in is HEAD when static\_fire.py runs.
You need to provide the four "twtr" keys in your config for auto tweet to work.
You can get these keys by creating a [Twitter app for your account](https://apps.twitter.com/).
Make sure your app was write and read access.

*Don't commit or share your config file! Especially if you store your Twitter app's OAuth keys in it.*

## Extra Bits

### Lying About Dates
Static Fire uses "author date" as the date an article was written.
You can pick an author date at commit time with the "git commit --date" option.
This won't change when an article appears on the your site. Only the date value under headers and in feeds.

### Text articles
Static Fire generates .text files next to your .html files for your website. This lets you see the Markdown of your article. For example:

https://shadedtriangle.com/articles/2017/10/review_golf_story.text

### Markdown Configuration
Markdown is configured by default to support footnotes[^1] and SmartPants style formatting.

### I Can't Commit my "config" File
You really shouldn't because it can have sensitive information.
To discourage you I hid it from git.
You can have it reappear in your working tree with.

    git upate-index --no-skip-worktree config

You can hide "config" again with:

    git update-index --skip-worktree config

[^1]: Like this.
