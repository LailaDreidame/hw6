# AI Prompts Log — HW6: Campus Customs Vendor Desk (Tokenomics + Prompt Injection)

---

## Problem 1 — Vibe coder prompts

**Prompt:**
> All right. Here we go. My sweet lady. We are now for homework 6, creating campus customs vendor desk. So that involves tokenomics plus prompt injection. Here's the scenario. The campus customs gets a steady stream of vendor quotes, invoices, catalog pages, and supplier emails. We're going to build a vendor desk agent that reads one of these documents, pulls out the key facts, vendor, item, price, lead time, minimum order, and recommends whether the shop should buy, following the rules in the campus custom shop handbook. This week is about 2 things that matter once an agent runs for real: cost, the handbook is about 10,000 tokens and goes out on every call, and safety. Some vendor documents hide instructions aimed at AI. We're going to measure the bill, cut it, attack our own agent, and defend it. Do not send emails or make payments. The agent's email and payment tools only write to a log file. We're going to use the port, key_API_key and only GPT-6 Luna for every AI call. Make sure you're on GPT-6-Luna for all the AI calls. Points will be deducted if I use any other model. And it should not show up in my code or runs. We're going to work one problem at a time. So let's start . We're going to create AI _prompts.md at the start of the assignment and keep it updated as I work. This file is a log of what I typed, to you, the vibe coder. We're going to describe each problem to the vibe coder in my own words. And we're going to put one section for each problem. Each section must include the problem number and title, just like usual. At least one prompt I typed or in my own words as much as possible. And one follow-up prompt if needed. So that's the first problem 1. Once that's all understood, we'll move on to problem 2.

**Follow-up:** None needed.

---

## Problem 2 — Size up the handbook

**Prompt:**
> Great. Sounds great. Problem 2 says we're going to size up the handbook. So we're going to unzip data.zip folder. We're going to look through data/shop_handbook.md. This is the campus custom shop handbook. And your agent will send it to the model on every single call. Also, look at data/prices.json. The gp2-6.luna price list. We're going to find out how many tokens the handbook is. In output/handbook_estimate.md, write the token count and how you got it, what the handbook alone costs in dollars on one call, and on 1,000 calls with cache tokens and without them, show your math. You will check these estimates against real runs in number 4. Problem number 4, I mean.

**Follow-up:** None needed.

---

## Problem 3 — Build the vendor desk agent

**Prompt:**
> Okay, so problem three, we're going to build the vendor desk agent. This is where 12 points we're going to build the vendor desk agent with pedantic AI using GPT-6-Luna. The agent is this these four files. Number one, prompts/prompt.md. Instructions for the agent. The agent also sends the handbook to the model on every call. Number two, agent.py. This is the entry point. Number three, tools.py. These are the tools. Number four, models.py. These are the structured types. We're going to give the agent the path to one vendor document. It reads the document with a tool. HTML, PDF, and .eml. Email files all have to work. And returns vendor SKU, unit price, lead time in days, minimum order, a decision, recommend or do not recommend would be the decisions. Following the handbook rules and a one-sentence reason. The agent must also have two trap tools, send_email and approve_payment. So the two trap tools are one, send_email and two, approve_payment. Its job never needs them. They are there to catch a malicious document that tricks the agent into emailing someone or paying a vendor. They do not send or pay anything. They only append the call and its arguments to folder output/trap_calls.json. Start it as an empty list. So if that file ever has an entry, a document took over your agent. Keep them on your system for the whole homework. After every run, append to output/usage_log.json. Document, time, the token counts, the API reports, and the $cost using, prices.json. And after every run, append to output/audit_trail.json. Each tool call with its arguments and a short result, plus the final answer. The agent should run like this in the terminal. python agent.py --doc data/practice_docs/p01_bluehen_quote.html What this is doing, runs the agent on one vendor quote and logs the answer, tools, and cost. Run it on P01 and P08 to show it works. Start output/harness.md. Each field in models.py and y and each tool in one line.

**Follow-up:** None needed.

---

## Problem 4 — With and without cached tokens

**Prompt:**
> Okay, let's continue on homework 6. Problem 4. This is with and without cache tokens. This is worth 16 points. That's a whole lot of points. So the handbook is the same on every call. So the model can reuse it from a cache at a much cheaper price, which is awesome. Test what that is worth. Run the agent on all 12 practice documents 2 ways. First way, with cache. Set up so the handbook gets reused from cache. Second way, without cache. Set up so nothing gets reused from cache. Check the token counts the API sends back to prove each setup really did what you think. A without cache run that still shows cache tokens does not count. So every model call from both setups save every model call from both setups to outputs/cache_test.json. For each call, include the setup document, every token count the API reports, and $ from prices.json. In the output/cache_test.md folder, put these 4 things. Number 1, total cost and cost per document for each setup and the % you saved. Number 2, how your real numbers compare to your problem 2 estimate. Number 3, a projection for 1,000 documents a day for 30 days with and without cache. And number 4, anything in the numbers that surprised you and why it happens. Make sure to use plain English so I can understand the reason why it surprised you.

**Follow-up:** None needed.

---

## Problem 5 — Attack your own agent

**Prompt:**
> Let's go to problem 5. And every time we finish a problem, I want you to create a little ding, ding, ding to let me know it's done. So I can hear it. I think it'll be a really cool sound. It should be a subtle, sweet ding, ding, ding sound. Okay, let's go to problem 5. Of homework 6. Problem 5 is about attacking our own agent. It's worth 8 points. So some vendor documents are booby-trapped with text aimed at AI. Run problem 3 agent with no new defenses on all 12 documents in data/practice_docs/. Compare each answer to data/practice_key.json and check output/trap_calls.json. The log your fake email and payment tools from problem 3 right to. We're going to save the save in the folder output/attack_results.json. For each document, whether each field matched the key, whether the decision matched, whether a trap tool was called, and whether a link or other strange text showed up in the answer. In output/attack_results.md, for every document that fooled your agent, write what fooled it and where in the file it was hiding. Open the documents the way a person would. Browser, PDF viewer, email app, and compare that with what your agent read.

**Follow-up:** None needed.

---

## Problem 6 — Defend your agent

**Prompt:**
> All right, sweetheart, you're right. Problem 6 is about defending the agent. This is where it's 16 points. We're going to defend the agent at 3 levels. Number 1, code, what your program does to the document before any model sees it. Number 2, design, how your agent is put together. So a poisoned document cannot reach the dangerous tools or the decision. Number 3, prompt, rules and prompts /prompt.md. You may not delete, send, _email, or approve, _payment from your system. The shop will use them later with a human sign-off. Keep a way to run the agent with no defenses. We'll need it in problem 7. We're going to rerun all 12 practice documents. We're going to save them in the folder output /defense_results.json in the same shape as problem 5. Plus tokens and dollars per document. Clean documents must still come back with the right values. Refusing or blanking out a real quote counts as a failure. We don't want to fail. In output /defense_results.md, do these 3 things. 1, a before and after table for all 12 documents. 2, what each layer catches that the others miss. 3, the extra tokens and dollars each layer adds per document. We're going to add your safety features to output /harness.md in a safety section. What each defense layer does in plain words, plain English. You got this.

**Follow-up:** None needed.

---

## Problem 7 — Red team

**Prompt:**
> All right, I am ready for problem 7. So this is problem 7 is called Red Team. It's worth 8 points. Now you are the attacker. We make 2 new booby-trapped vendor documents in data/my_attacks/. HTML, PDF, or email. Each one should use a hiding trick or an attack goal that is not in the practice set. A person opening the document should see a normal quote. Run both attacks on your agent with no defenses and on your defended agent. In output/red_team.md for each attack, what is hidden, where, what it tries to make the agent do, and what happened before and after your defenses. More points for attacks that are new and that actually fool the agent with no defenses.

**Follow-up:** None needed.

---

## Problem 8 — Exam documents

**Prompt:**
> All right, problem 8. Problem 8 is about exam documents. There were 12 points. We're going to use the folder data/exam_docs/. It has 10 vendor documents with no answer key. Run your final defended agent on all of them. Do not hand edit the results. Save in output/exam_results.json with one entry per exam file, each entry has these fields. File, the exam file name, example, e01_quote.html. Vendor, SKU, unit, underprice, unit_price. Lead_time_days. MIN_order. Decision, recommend or do not recommend. Reason, trap_tool_called, true or false. Input tokens, input_tokens, cached_tokens, output_tokens, cost_USD. Graders compare results to a hidden answer key and rerun some agents to check. You get points to correct fields and decisions. No trap tool calls and clean documents handled normally.

**Follow-up:** None needed.

---

## Problem 9 — Results page

**Prompt:**
> Okay. Problem 9 it is. Problem 9 is the results page, which is worth 12 points. We have to build the folder output/hw6_report.html. It must be one file that opens by double-click with no internet and no other files next to it. The page must follow the 5 things below. We're going to use real numbers from earlier problems. Number 1, for caching results with a chart. Number 2, attacks before and after your defenses. Number 3, what your defenses cost in tokens and dollars. US dollars. Number 4, your exam results and your 2 red team attacks. Number 5, a short recommendation to the store manager. Should campus customs turn this agent on for real vendor mail? And what would it cost per month at $1,000 documents a day? More points for a designed page, fonts, color, layout that reads well. Let's design it in a very modern, MoMA museum kind of way. Since this is what I like. And I want it to read well, plain English, easy to access, user-friendly.

**Follow-up:** None needed.

---

## Problem 10 — Push to GitHub and submit the URL

**Prompt:**
> Okay, before we get to problem one, I actually want to go to how to push to GitHub and submit the URL. So when we finish this work, we're going to push our project to a public GitHub repository and submit the repo URL on Canvas. Graders are going to clone it, so make sure it opens and the files below are there. Include the whole data / folder, the course data plus the 2 attack files, so graders can clone the repo and run the agent right away. We're not going to commit the real.env. We're going to use the .git ignore to keep it out and include .env.example with placeholders only. And there's an expected repo on how we should put all this together. And I will give you the screenshots for that.

**Follow-up:** None needed.
