# TL;DR News — Marketing & Traffic Growth Strategy

**Starting point:** Zero visitors
**Site URL:** https://bkarras12.github.io/TLDR-NEWS/news/reports.html
**Date:** March 2026

---

## What You Have (Strengths to Leverage)

Before spending a dollar or an hour on marketing, understand what makes this site genuinely useful:

1. **Fresh daily content, automatically generated** — most news aggregators require manual curation. Yours runs on autopilot 3x/day.
2. **AI-powered analysis** — not just headlines, but sentiment scores, key themes, future outlook, and risk/opportunity signals. This is a real differentiator.
3. **5 categories** covering world, business, tech, sports, and science from reputable sources (BBC, Guardian, The Verge, ESPN, ScienceDaily).
4. **RSS feeds already built** — you have `feeds/all.xml` and per-category feeds ready for syndication.
5. **Clean, fast, no-JS-framework site** — loads instantly, works on any device.
6. **Sentiment trend charts** — visual data that's shareable and screenshot-worthy.

---

## Phase 1: Foundations (Week 1–2) — Cost: $0

These are the things you do *before* promoting anywhere. Skipping these means wasted effort later.

### 1.1 Fix Your SEO Basics

Your sitemap URLs are currently relative paths (e.g., `news/reports.html` instead of full URLs). Search engines need absolute URLs.

**Action items:**
- [ ] Update `sitemap.xml` to use full absolute URLs: `https://bkarras12.github.io/TLDR-NEWS/news/reports.html`
- [ ] Submit your sitemap to [Google Search Console](https://search.google.com/search-console) — this is free and tells Google your site exists
- [ ] Submit to [Bing Webmaster Tools](https://www.bing.com/webmasters) — also free, covers Bing + DuckDuckGo
- [ ] Add a canonical URL meta tag to `reports.html`: `<link rel="canonical" href="https://bkarras12.github.io/TLDR-NEWS/news/reports.html">`

### 1.2 Set Up Free Analytics

You can't improve what you can't measure.

**Action items:**
- [ ] Add [Plausible Analytics](https://plausible.io/) (privacy-friendly, free self-hosted or $9/mo hosted) OR [Google Analytics 4](https://analytics.google.com/) (free) — a single `<script>` tag in `reports.html`
- [ ] Set up a [Google Search Console](https://search.google.com/search-console) property — this shows you what search queries lead to impressions/clicks

### 1.3 Create Your "About" Identity

People share content from sources they trust. Right now your site has no identity beyond the brand name.

**Action items:**
- [ ] Write a short "About TL;DR News" section (can be a footer expansion or a simple about page) explaining: *"AI-generated daily intelligence briefs from BBC, The Guardian, The Verge, ESPN, and ScienceDaily. Updated 3x daily. No ads, no tracking, no paywalls."*
- [ ] Create a simple Open Graph image (1200x630px) for social sharing — use Canva (free) with your brand colors (#06080f background, #00e5ff accent, "TL;DR News" text). This is the image that appears when someone shares your link on Twitter/LinkedIn/Reddit.
- [ ] Add `og:image` meta tags to `reports.html` and `articles.html`

---

## Phase 2: Content Distribution (Week 2–4) — Cost: $0

This is where you get your first 100–500 visitors. The strategy: go where people already are, and give them a reason to click.

### 2.1 Reddit (Highest ROI for a new site)

Reddit is the single best free traffic source for a niche content site. But you need to be a community member, not a spammer.

**Target subreddits:**
| Subreddit | Subscribers | Angle |
|---|---|---|
| r/artificial | 500k+ | "I built a fully automated AI news pipeline" — share the tech behind it |
| r/SideProject | 100k+ | "My side project: AI-generated daily news briefs from 5 sources" |
| r/InternetIsBeautiful | 17M+ | "TL;DR News — free AI-generated daily intelligence briefs" |
| r/technology | 15M+ | Share specific interesting AI-generated insights from your reports |
| r/worldnews | 32M+ | Share notable analysis (carefully, follow sub rules) |
| r/DataIsBeautiful | 20M+ | Screenshot your sentiment trend charts with commentary |
| r/webdev | 2M+ | "I built a zero-dependency vanilla JS news dashboard" — technical angle |
| r/Python | 2M+ | "Python pipeline that auto-generates AI news reports daily" |
| r/opensource | 200k+ | If you open-source the pipeline code |

**Reddit playbook:**
1. Create a Reddit account (or use existing one) and spend 3–5 days commenting genuinely in these subs before posting your own content
2. Write a "Show Reddit" style post in r/SideProject or r/artificial: *"I built a fully automated news intelligence dashboard — Python pipeline fetches RSS from BBC, Guardian, The Verge, ESPN, ScienceDaily, then GPT-4o generates analysis with sentiment, themes, and outlook. Runs 3x daily on GitHub Actions. Zero cost to host."*
3. Include 2–3 screenshots of the dashboard (dark mode looks great for Reddit)
4. **Respond to every comment** — this keeps the post alive in the algorithm
5. Post to ONE sub at a time, spaced 3–5 days apart. Cross-posting the same day looks like spam.

**Expected result:** A well-received r/SideProject post typically gets 50–500 upvotes and 200–2,000 clicks. One viral r/InternetIsBeautiful post can drive 5,000–50,000 visits in 48 hours.

### 2.2 Hacker News

HN readers love technically interesting projects, especially ones with clean architecture.

**Action items:**
- [ ] Write a "Show HN" post: *"Show HN: TL;DR News — Automated daily AI news briefs from 5 RSS sources"*
- [ ] Best posting times: Tuesday–Thursday, 9–11 AM ET
- [ ] If you write a blog post about the architecture (GitHub Actions + Python + OpenAI structured outputs + vanilla JS), submit that — HN prefers blog posts over "look at my thing"
- [ ] Be prepared to answer technical questions about the pipeline, model choices, and structured output schemas

**Expected result:** A front-page HN post drives 5,000–30,000 visits in 24 hours. Even a post that gets 10–30 points sends 200–1,000 targeted visitors.

### 2.3 Twitter/X

Your daily reports are perfect for Twitter's format.

**Action items:**
- [ ] Create a @TLDRNewsAI account (or similar)
- [ ] **Automate daily tweets** — Add a step to your GitHub Actions workflow that tweets the day's key takeaway for each category. Format: *"Today's AI news brief: [Key takeaway from technology report]. Full analysis with sentiment trends: [link]. #TechNews #AI"*
- [ ] Share your sentiment trend chart screenshots — visual data gets 2–3x more engagement
- [ ] Follow and engage with accounts in the AI/tech/news space
- [ ] Quote-tweet major news stories with your AI's analysis as added context

**Automation approach (free):** Use the Twitter API v2 free tier (1,500 tweets/month) with a Python script in your GitHub Actions workflow that posts after the pipeline runs.

### 2.4 LinkedIn

LinkedIn is underrated for driving traffic to professional/analytical content.

**Action items:**
- [ ] Post your business/technology category insights as LinkedIn articles
- [ ] Frame it as professional intelligence: *"What AI says about today's business headlines — automated analysis from BBC, Guardian, and The Verge"*
- [ ] Use the "document" post format (carousel/PDF) to share visual breakdowns of your sentiment data

### 2.5 Product Hunt Launch

When you're ready (after fixing SEO basics and having analytics), do a Product Hunt launch.

**Action items:**
- [ ] Create a Product Hunt maker profile
- [ ] Prepare 5–6 screenshots/GIF showing the dashboard, sentiment charts, category switching
- [ ] Write a compelling tagline: *"AI-generated daily news intelligence — updated 3x/day from 5 trusted sources"*
- [ ] Launch on a Tuesday or Wednesday (best PH days)
- [ ] Rally friends/colleagues to upvote in the first 2 hours (this matters a lot for PH ranking)

**Expected result:** A top-10 daily PH launch drives 2,000–10,000 visits and gets you featured in PH newsletters (100k+ subscribers).

---

## Phase 3: Organic Growth Engine (Week 4–8) — Cost: $0–$50

### 3.1 Newsletter / Email List

Email is the only traffic channel you truly own. Everything else (Reddit, Twitter, Google) can change its algorithm overnight.

**Action items:**
- [ ] Set up a free [Buttondown](https://buttondown.email/) newsletter (free up to 100 subscribers) or [Substack](https://substack.com/) (free)
- [ ] Add an email signup form to your site — a simple banner: *"Get the daily AI news brief in your inbox. 5 categories. 3 minutes to read."*
- [ ] Automate the email: your pipeline already generates the content. Add a step that formats the executive summary + key takeaway from each category into a daily email and sends it via Buttondown/Substack API
- [ ] This becomes your most valuable asset over time. Even 500 email subscribers is worth more than 5,000 Twitter followers.

### 3.2 RSS Syndication

You already have RSS feeds built. Now make them discoverable.

**Action items:**
- [ ] Submit your RSS feeds to aggregators:
  - [Feedly](https://feedly.com/) — search for your feed URL and claim it
  - [Inoreader](https://www.inoreader.com/)
  - [NewsBlur](https://newsblur.com/)
  - [Feedspot](https://www.feedspot.com/) — submit to their "Top AI News" and "Top News Aggregator" lists
- [ ] The RSS `<link>` URLs in your feeds currently use relative paths — update them to absolute URLs so they work when consumed by feed readers

### 3.3 SEO Content Play (Medium-Term)

Your articles page is a content engine waiting to be used. Each article is a potential Google search result.

**Article ideas that rank well:**
- "Daily AI News Summary: [Date]" — people search for this
- "Weekly Technology Trends: What AI Sees in This Week's Headlines"
- "Sentiment Analysis of World News: [Month] 2026"
- "How BBC, Guardian, and The Verge Covered [Major Event] Differently"

**Action items:**
- [ ] Publish 1–2 articles per week using your pipeline data as source material
- [ ] Target long-tail keywords: "daily AI news summary", "automated news analysis", "news sentiment tracker"
- [ ] Each article should link back to the relevant daily report on your site

---

## Phase 4: Community & Partnerships (Month 2–3) — Cost: $0

### 4.1 GitHub Stars & Open Source Community

Your project is technically impressive. The open-source community is a real audience.

**Action items:**
- [ ] Make sure your GitHub repo has a compelling README with screenshots, architecture diagram, and a "How it works" section
- [ ] Add your live site link prominently in the repo description
- [ ] Submit to [awesome-selfhosted](https://github.com/awesome-selfhosted/awesome-selfhosted) list
- [ ] Submit to [awesome-python](https://github.com/vinta/awesome-python) list
- [ ] Post on r/selfhosted: *"Self-hosted AI news aggregator — Python + OpenAI + GitHub Pages"*

### 4.2 Cross-Promotion with Other Newsletters

Many small newsletter operators do "recommended reads" sections.

**Action items:**
- [ ] Find 10–15 newsletters in the AI/tech/news space with 1k–10k subscribers
- [ ] Reach out offering a mutual recommendation or a guest piece about your automated pipeline
- [ ] Tools to find newsletters: [Letterlist](https://letterlist.com/), [Newsletter Stack](https://newsletterstack.com/)

### 4.3 AI Tool Directories

There are dozens of directories listing AI-powered tools. Most accept free submissions.

**Submit to:**
- [ ] [There's An AI For That](https://theresanaiforthat.com/)
- [ ] [FutureTools](https://www.futuretools.io/)
- [ ] [AI Tool Directory](https://aitoolsdirectory.com/)
- [ ] [TopAI.tools](https://topai.tools/)
- [ ] [Toolify.ai](https://www.toolify.ai/)

---

## Phase 5: Paid Amplification (Optional, Month 3+) — Cost: $50–$200/month

Only do this after you have analytics showing what content resonates and you've built some organic traction.

### 5.1 Reddit Ads

- Target r/technology, r/artificial, r/worldnews with promoted posts
- Budget: $5–10/day, CPC ~$0.30–0.80
- Use your best-performing organic Reddit post as the ad creative

### 5.2 Twitter/X Ads

- Promote your best-performing tweets
- Budget: $5/day minimum
- Target followers of @BBCWorld, @guardian, @veraborz, @techmeme

### 5.3 Google Search Ads

- Target: "daily news summary", "AI news aggregator", "news sentiment analysis"
- Budget: $100–200/month
- Only worth it once your site converts visitors (has email signup or clear value prop)

---

## Quick Wins Checklist (Do These This Week)

| Priority | Action | Time | Expected Impact |
|---|---|---|---|
| 1 | Fix sitemap URLs to absolute paths | 30 min | Google can properly index your site |
| 2 | Submit to Google Search Console | 15 min | Google discovers your site within days |
| 3 | Add analytics (Plausible or GA4) | 15 min | You can measure everything going forward |
| 4 | Create OG image for social sharing | 30 min | Links look professional when shared |
| 5 | Write a Show HN post | 1 hour | Potential for 1,000–30,000 visits |
| 6 | Write a r/SideProject post with screenshots | 1 hour | 200–2,000 targeted visitors |
| 7 | Submit RSS feeds to Feedly/Feedspot | 20 min | Ongoing passive traffic from RSS readers |
| 8 | Submit to 3–5 AI tool directories | 30 min | Backlinks + ongoing referral traffic |
| 9 | Set up a Buttondown/Substack newsletter | 30 min | Start building the email list from day one |
| 10 | Create Twitter account, post first 5 reports | 1 hour | Ongoing distribution channel |

---

## Metrics to Track

| Metric | Tool | Target (Month 1) | Target (Month 3) |
|---|---|---|---|
| Daily unique visitors | Plausible / GA4 | 50–100 | 500–1,000 |
| Google Search impressions | Search Console | 500 | 5,000 |
| Google Search clicks | Search Console | 20–50 | 200–500 |
| Email subscribers | Buttondown/Substack | 25–50 | 200–500 |
| Twitter followers | Twitter Analytics | 50–100 | 500+ |
| Reddit post upvotes | Reddit | 50+ on first post | Multiple posts with 100+ |
| GitHub stars | GitHub | 20–50 | 100–200 |
| RSS feed subscribers | Feedly (shows count) | 10–20 | 50–100 |

---

## What NOT to Do

1. **Don't spam.** Posting your link in 10 subreddits on the same day will get you banned and your domain flagged.
2. **Don't buy followers/traffic.** Bot traffic destroys your analytics signal and wastes money.
3. **Don't invest in paid ads before you have analytics and a working email signup.** You're paying to send people to a site with no way to retain them.
4. **Don't overthink the design.** Your site already looks professional. Ship the marketing before perfecting the product.
5. **Don't try to compete with CNN or Google News.** Your angle is AI analysis + sentiment + outlook — lean into that unique value.

---

## The 30-Second Pitch (Use Everywhere)

> **TL;DR News** is a free, AI-powered daily news intelligence dashboard. Every morning, it automatically pulls headlines from BBC, The Guardian, The Verge, ESPN, and ScienceDaily, then uses GPT-4o to generate analysis with sentiment scores, key themes, risk/opportunity signals, and future outlook. No ads. No paywall. Updated 3x daily.

---

*This strategy prioritizes free, high-impact channels appropriate for a zero-to-one launch. Revisit and adjust after 30 days of analytics data.*
