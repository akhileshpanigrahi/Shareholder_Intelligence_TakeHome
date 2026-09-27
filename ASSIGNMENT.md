# Take-home — Shareholder Intelligence for one issuer

**Time:** 8 hours of your time, spread over one week. Tell us where you stopped.

**Tools:** Any database, any language. You may use Claude or another assistant. Send us the prompts you used.

**Submit:** One repository or zip. A README that says how to run it.

## The situation

Northwind Metals Corp is a US public company. We are its transfer agent. That means we keep the official list of who owns its shares. This list is the share register.

Most shares sit in the name of one nominee, CEDE & CO. Behind that one line are brokers and their clients. We cannot see them. We see only the total.

Large owners must tell the SEC when they hold 5% or more. They file a form, SC 13D or SC 13G, some days after the event. Those filings are public. They are the only window into the shares behind the nominee.

Northwind's CFO opens our product every Monday. She wants to know who bought, who sold, who is new, who left, and who to worry about. She downloads a list for the board.

## The data (folder `data/`)

| File | What it is |
|---|---|
| `holders.csv` | The holders on our register. A holder can have more than one version. `valid_from` says when a version starts. |
| `opening_positions.csv` | Shares per holder at close of 31 May 2026. |
| `register_events.csv` | Every register change from 1 June to 31 August 2026. `effective_date` is the day the change counts from. `recorded_at` is when we wrote it down. `reverses_transfer_id` points to the transfer a reversal undoes. |
| `shares_outstanding.csv` | Total shares the company reports, with the date it counts from and the date it was published. |
| `beneficial_filings.csv` | SC 13D and SC 13G filings for Northwind. `amends_accession_no` points to the filing an amendment replaces. `event_date` is when the holding changed. `filing_date` is when the SEC received the form. |

The data is synthetic. It has faults in it. Real feeds have the same faults. Treat every fault you find as part of the job. List them.

## What to deliver

### 1. A schema and a loader

Tables, in SQL. A script that loads all five files. The loader must run twice and give the same result.

### 2. Six questions, answered with queries

Each answer is a query we can run, plus the result. For each one, say what you decided and why.

1. **Top holders.** The ten largest owners of Northwind on 31 August 2026, from both sources together, one line per real owner. Show the shares we hold on the register, the shares reported to the SEC, and your best number for the total.
2. **Last week.** Who bought and who sold in the week of 24 to 28 August 2026, by holder type. Same shape as the screen the CFO opens on Monday 31 August.
3. **Percent of the company.** For every SEC filer, the percent they hold, computed by you. Show it next to the percent they reported. Explain every difference.
4. **Watch list.** Every holder who crossed 5% or 10% in either direction between 1 June and 31 August, and every filer who changed from a 13G to a 13D. Give the date, and say whether the date is when it happened or when we learned about it.
5. **Then and now.** The register position of Sable Point Advisors on 31 July 2026 as we knew it on 31 July, and as we know it today. Explain the difference.
6. **Does it add up?** Prove, with a query, whether the register total agrees with the company's shares outstanding on 30 June and on 31 August. If it does not, say by how much and why.

### 3. The Monday screen, built

Build the screen the CFO opens on Monday 31 August 2026. Use any tool: Streamlit, Metabase, plain HTML, a notebook, a spreadsheet. It must read from the database your loader filled. It must run on our machine from your README.

Decide what she sees first, second, and third, and why. Decide what needs a colour, a flag, or a number that stands out. Decide what she can download. Put on the screen, in plain words, what the product cannot know.

Then write half a page for her: the three alerts the product sends, with the exact rule behind each.

### 4. How it stays right, on one page

The register changes all day. Filings arrive once a day. The screen and the download must show the same numbers, and they must be right. Write one page for an engineer on how the data behind the screen is kept correct. Cover: how a change on the register reaches the screen, and how fast; what happens on the screen when a reversal for last Tuesday arrives today; what "as of" means on the screen; how you know when the data is stale or the load has failed.

### 5. Fault list

Every fault you found in the data, one line each, with what you did about it.

## What we look at

- Do the numbers reconcile, and did you say so when they do not.
- Did you decide what the CFO sees, or did you show her every table.
- Did the schema keep both the date a thing happened and the date we learned it.
- Did you treat one real owner as one owner across name changes, two sources, and two systems.
- Is the writing plain enough for a CFO to act on without calling you.
