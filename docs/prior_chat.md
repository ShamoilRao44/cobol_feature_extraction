Claude
Shared by Shamoil Rao. This is a copy of a chat between Claude and Shamoil Rao. Content may include unverified or unsafe content that does not represent the views of Anthropic. Shared snapshot may contain attachments and data not displayed here.
Files hidden when shared

Read memory, read a page, searched the web
Read memory, read a page, searched the web
I can't tell what you want from this screenshot. Here's what I could check about the repo it's discussing.

It's a small personal project. The owner describes it as a mainframe banking application with COBOL programs, DB2 integration, JCL batch orchestration and transaction processing. The search only returned the profile blurb, not the source, so I haven't seen the COBOL or JCL either, same as the other chat. 
github

My view: it's fine as a smoke test for a pipeline but poor as a benchmark. A hobby repo is likely to be small and clean, with no CICS, BMS maps, missing copybooks or messy fixed-format quirks. Those are exactly the things you said break your tools on real projects. Your Danish customer_search_isolated folder is a much harder test.

What do you want me to do with it? For example, I could continue the repo-to-Flask design, or build the Stage 1 classifier test around it.

I want you to help me design the process of modernization

Here's a simple end-to-end process. It builds on your PUD stages and adds the modernization half.

Phase A: Understand (your PUD stages 1-5)

Inventory and classify every file (program, copybook, JCL, BMS, SQL) and list what's missing.
Extract structure with a parser, not the LLM: calls, copybook usage, SQL tables, files, job steps.
Summarize bottom-up with the LLM, one program at a time.
Synthesize into business flows (for example, "post daily transactions"), each as a chain from JCL job to programs to tables.
Verify and flag gaps, and review the PUD at a checkpoint.
Phase B: Design the target
6. Map each flow to Flask: JCL job → CLI/service function, CICS screen → page plus API, COBOL record → model.
7. Design the DB schema from the DB2 DDL and copybooks. Map COMP-3 to Decimal.
8. Review the design at a checkpoint.

Phase C: Generate per flow
9. Order the work by dependencies, leaves first.
10. Generate tests first, inferred from the logic: branches, boundaries, error paths.
11. Generate the code for one unit at a time, fitting well within 250k context.
12. Run the tests. If they fail, feed the error back to the LLM, up to N retries, then flag for a human.
13. Save state after each unit so you can resume.

Phase D: Assemble
14. Wire the app (routes, config, DB connection) and run an end-to-end flow test.
15. Final report: code, intermediate documents, and an assumptions/open-issues list.

Three rules apply throughout:

Use deterministic parsing wherever possible, and use the LLM only for meaning and code.
Missing source gets a flagged assumption, never a stop.
Humans only review at the PUD, the design and the final report.
Do you want to go deeper on one phase first, or should I turn this into a flow diagram?

9kay so now we will develop a software that would be incrementally devloped stage by stage and tested on the this repos code on my local machine with groks free api key for llm purposes. We will start with stage 1 inventory and classify. You dont have to code. You have to first discuss with me, ask me questions give me and yourself a clear picture of what we want to do at a moment then create a detailed prompt that can be given to copilot in vscode such  taht it just have to act as a dumb programmer, deciding in nothing kust writing code. So that is how we will be working.

Here's my starting picture of Stage 1, which you can correct.

Stage 1 does one thing: scan a folder, classify each file (COBOL program, copybook, JCL, BMS, DB2 DDL, data, other), and write an inventory.json that later stages read. It uses no LLM, only regex and file rules. Grok isn't needed until Stage 3, so Stage 1 stays simple and testable.

We'll go one question at a time. First:

Is the repo already cloned on your machine? If so, what do the top-level folders and a few sample filenames inside them look like? (For example, are the COBOL files .cbl, .cob or extension-less?) If you don't have it yet, say so and we'll start from the file extensions listed in the README.

Files hidden when shared
Here i have attached the repo. Remeber the solution we are making will be just tested on this repo. Its not the end goal. Menaing the solution mist be architecture agnostic as in which file resides where should not affect the working. The only thing relevant to any part of this solution should be the code in a file.


Ran 2 commands, updated memory
Ran 2 commands, updated memory
I unzipped the repo. It's tiny: 4 COBOL programs, 2 JCL jobs, and 8 markdown docs. It does fit your layout-agnostic rule, and it's good for testing gaps:

Missing source: the programs COPY ACCTREC, SQLCA, ERRHDLR and TRANREC, but no copybook files exist. The job DAILY runs TRANPROC, which also isn't there.
No DB2 DDL file exists, even though the programs use EXEC SQL.
Format: the code is free-ish, starting at column 8 with no sequence numbers. It's not the strict fixed-format of your Danish sample.
Stage 1 design so far

It classifies by content only. It ignores folders and extensions, and reads the first N lines of each file for signatures such as IDENTIFICATION DIVISION/PROGRAM-ID, //NAME JOB, EXEC SQL, and level numbers with PIC.
It outputs one inventory.json with a record per file: path, detected type, confidence, line count, encoding, and line-ending style.
It records unresolved references (copybooks, called programs, and so on), so the gaps are recorded from the start.
Question: should the inventory include non-code files, such as the markdown docs, labelled as documentation, or should it skip them? I'd keep them. The .md files here describe the architecture, and later stages could use them as context, but they'd be marked as non-authoritative. Keep or skip?

I think this repo wont be a good benchmark for all scenarios. Can you search for repos that could better serve our purpose


Searched the web
Searched the web
Two public repos fit much better:

AWS CardDemo (open-sourced by AWS). It's built to exercise analysis and migration tooling, and its README says the coding style is not uniform across the application, which is useful for testing. It combines COBOL, CICS, VSAM, JCL, RACF and assembler. The expected layout has separate JCL, PROC, CBL, CPY, BMS, ASM and MACLIB sets. That gives you every file type Stage 1 needs to tell apart. DB2 is optional, so it has little embedded SQL. 
aws mainframe modernization carddemo
 +2
CBSA (IBM's CICS Banking Sample Application, cicsdev on GitHub). It simulates a bank from the teller's point of view and demonstrates CICS, COBOL, BMS, Db2 and SQL, among other technologies. It's the best fit for CICS plus DB2 together. It also has Java and REST layers, which makes it a good test that those files get classified as "other". 
github
I'd test Stage 1 on four sources:

CardDemo for breadth of file types.
CBSA for CICS plus DB2.
Your current banking repo for missing copybooks and missing programs.
Your Danish customer_search_isolated folder for extension-less, fixed-format, mixed line-ending files.
Together they cover almost every case we need. To keep Stage 1 layout-agnostic, I'll also tell Copilot to ignore folder names and extensions completely, and I'll keep the markdown docs in the inventory as "documentation" unless you object.

Can you clone CardDemo and CBSA locally and zip them up for me? I'll look at the real files before we write the Copilot prompt.

Okay we will do that, we will test it on them. One point that i think i should mention so that you plan and design accordingly if relevant is that. We go to know that the cobol written for ibm z/os mainframe codebase is omewaht diffrent from the original cobol language. Something about cobol 85 and cobol 6 or something. That leads to parsers like proleap failing on out mainframe code bases.

That matters mostly for Stage 2, but it affects how I design Stage 1.

What I know (as far as I know): ProLeap-style parsers are built on a grammar close to standard COBOL-85. IBM Enterprise COBOL (V5/V6) adds things that grammar doesn't cover, such as JSON PARSE/GENERATE, XML PARSE, compiler-directing cards like CBL/PROCESS, newer data types and intrinsic functions, and embedded EXEC SQL/EXEC CICS blocks. One unknown construct can make a strict parser fail on the whole file.

What this means for the design:

Stage 1 must not use a real COBOL parser. It stays with regex and content signatures, so one odd construct can't make a file "unreadable".
Stage 2 shouldn't depend on one full parser. It should extract only the facts we need (COPY, CALL, EXEC SQL/CICS, file SELECTs, PERFORM, data items) using tolerant line-based patterns, and be able to continue past a part it doesn't understand. The LLM could fill in those parts later.
Stage 1 will record a few cheap hints per COBOL file: source format (fixed columns or free), whether it has EXEC SQL, EXEC CICS or COPY, and whether it has CBL/PROCESS cards. These tell later stages how to treat the file.
Question: do you remember what kind of failures ProLeap gave you on the real code, such as a specific construct, a crash on a whole file, or silently missing output? If you have an error message or a snippet, send it and I'll make sure Stage 2 handles that case.

Actualay i dont inderstand how a language parser works so i didnt understnd what was what. I think before teying to modernize mainframe cobol project i think o should know basic of how a cobol based mainframe works. Tell me can i run a sample codebase like the aws one you mentioned on my windows machine. At least emulate it. If yes then how and what would i need


Searched the web
Searched the web
Short answer: you can't fully run CardDemo on a Windows laptop for free. Someone who tried to push the free path as far as they could on CardDemo concluded that running the COBOL/CICS/VSAM/JCL paths needs a real or licensed-compatible legacy runtime. You can still learn the basics and run pieces of it. 
huggingface

What the pieces are

COBOL program: business logic, usually a batch program.
JCL: the job script. It says "run program X, with these files attached."
Copybook: a shared include file, mostly record layouts.
CICS and BMS: online transactions and 3270 screens.
DB2 and VSAM: a relational database and indexed files.
What you can do on Windows

GnuCOBOL (free). It implements a substantial part of the COBOL 85, 2002 and 2014 standards, plus many extensions from other compilers, and runs on Windows. You can compile and run plain COBOL programs, for example your banking repo's batch programs with a few stand-in files, but there's no real JCL, CICS or DB2. It's also not IBM's dialect, so it can reject some IBM-specific syntax. 
github
Hercules with TK4- (free). It gives you a working MVS 3.8j environment on Windows, Linux and Mac, but you'll need a 3270 emulator. It's real JCL and job flow, but 1980s-era COBOL, so it's good for learning how a mainframe works, not for running CardDemo. 
openmainframeproject
IBM's COBOL for VS Code. IBM COBOL can be obtained free of charge by applying for the COBOL environment for VS Code, part of the Open Mainframe Project. Use this for editing, and check the current terms yourself. 
exercism
A real z/OS in the cloud, for example IBM's free learning programs (Master the Mainframe, Z Xplore) or the Open Mainframe Project's COBOL course. I haven't verified their current sign-up terms, so check before relying on them.
What I'd do: you don't need to run CardDemo to build Stage 1, because it only reads files. To learn how the pieces fit, install GnuCOBOL and run one small batch program from your banking repo, then follow a JCL job by hand to see which program and files it uses. That will give you enough background to follow the design.

Do you want me to write a short, step-by-step GnuCOBOL setup for that?

Can you explain wiha real world example how cobol works code wise


Ran a command
Ran a command
I'll use a real program from your banking repo, INTCALC, which posts monthly interest to savings accounts.

1. A COBOL program has four divisions, like four sections of a form

IDENTIFICATION names the program.
ENVIRONMENT says which files it uses. Here SELECT INTEREST-REPORT ASSIGN TO UT-S-INTRPT points at a report file, and the real file is attached by the JCL.
DATA declares every variable up front.
PROCEDURE holds the logic.
2. Variables are declared by their shape, with PIC

cobol
05 WS-ACCOUNT-BALANCE  PIC S9(11)V99 COMP-3.
05 WS-ACCT-TYPE        PIC X(1).
S9(11)V99 is a signed number with 11 digits, an implied decimal point and 2 decimals.
X(1) is one character.
COMP-3 means "stored as packed decimal". It's exact money arithmetic, which is why it matters in banking, and Python needs Decimal to match it.
The numbers 01 and 05 nest fields into records. This is how WS-INTEREST-CALC is a group of fields.
3. The logic is named paragraphs called with PERFORM

cobol
000-MAIN-PROCEDURE.
    PERFORM 100-INITIALIZATION.
    PERFORM 200-PROCESS-INTEREST.
    PERFORM 300-FINALIZATION.
    STOP RUN.
It's like calling functions, except there are no parameters. Every paragraph reads and writes the same shared variables.

4. SQL is embedded between EXEC SQL … END-EXEC
It declares a cursor over active savings and money-market accounts, then loops with FETCH. :WS-ACCT-NUMBER is a COBOL variable receiving a column value. After each statement, SQLCODE says whether it worked (0 means yes).

5. What happens per account:
COMPUTE interest = balance × rate / 12 → UPDATE the balance → INSERT a transaction row → WRITE a line to the report.

Where COPY ACCTREC and COPY SQLCA fit: they paste in shared layouts from other files. Those files are missing here, which is the gap your Stage 1 inventory should flag.

Reading this made me notice a small flaw: the UPDATE ... SET is missing a comma between two columns, so this code likely never compiled as is. That's another reason this repo is a weak benchmark.

Want me to walk through how DAILY.jcl runs these programs next, so you see the whole batch flow?

No i mean from ghe user and machine perspective. Like user first see this which is displayed by this then user enters this then what files is caleed that decides what should be caleked then what user sees like that


Searched the web
Searched the web
Here's the online flow, from the user's side and the machine's side. I'm using CardDemo's sign-on and menu as the example. I confirmed that sign-on is the program COSGN00C, which checks the USRSEC file. The other program names below are illustrative.

1. The user types a transaction code (for example CC00) on a 3270 terminal screen

CICS looks up the code in a table: transaction code → program. That table is CICS configuration, not COBOL.
It starts the program COSGN00C.
2. The program shows the sign-on screen

The program runs EXEC CICS SEND MAP(...).
A BMS map is the screen layout: where the labels and the input fields (User ID, Password) sit.
The program then does EXEC CICS RETURN TRANSID(...) COMMAREA(...), which ends the program. Nothing is running while the user types. This is the pseudo-conversational design: CardDemo programs save context in the COMMAREA on return and restore it on entry. 
onrender
3. The user types an ID and password and presses Enter

CICS starts the same program again. It sees from the COMMAREA that this isn't the first visit, so it takes the "process input" path.
It runs EXEC CICS RECEIVE MAP(...), which fills COBOL variables from the screen fields.
4. The program decides what's next

It reads the user file (USRSEC) with EXEC CICS READ FILE(...), using the user ID as the key. CardDemo validates the user ID against USRSEC during sign-on. 
onrender
Wrong password → it sets an error message and sends the sign-on screen again (back to step 2).
Correct → it stores the user's details in the COMMAREA and passes control with EXEC CICS XCTL PROGRAM('menu program'). Which menu depends on the user type, regular or admin.
5. The menu program shows the menu map, and the user types option 2 and presses Enter. The program checks the choice and uses XCTL to hand off to the program for that function, for example account view. That program sends its own map and keeps the same cycle (send, return, receive, decide).

The pattern: every screen is a map, every step is a program that runs briefly and ends, a COMMAREA carries state between steps, and XCTL/LINK choose the next program. CardDemo chains these as Menu → Function → Detail → Update. 
onrender

Why this matters for modernization: each map becomes a web page, each program step becomes a route or API handler, and the COMMAREA becomes a session or request state. Stage 1 will flag which files are the maps and which programs use EXEC CICS.

Does this match what you wanted? Next I can draw this as a flow diagram.

So when this program is converted to a flask applicatiom how would taht work such that core business logic remains same

The idea is to separate what the business rules are from how the user reaches them. COBOL mixes the two in one program. The Flask version splits them.

How the sign-on example maps

COBOL/CICS	Flask
Transaction code	URL route (/login)
BMS map (screen)	HTML template
SEND MAP / RECEIVE MAP	Render the template / read the submitted form
Pseudo-conversational loop and COMMAREA	Not needed. HTTP is already request-based, and session or token holds the user state
READ FILE(USRSEC)	Query on a users table
XCTL to the menu program	Redirect to /menu
Where the business logic lives
You pull the rules out into plain Python functions that know nothing about screens or the web:

python
def authenticate(user_id, password) -> User | None: ...
def calculate_interest(balance: Decimal, rate: Decimal) -> Decimal:
    return balance * rate / 12
The Flask route is then thin: read the form, call the function, render the result. The same function can be called from a route, a batch job, or a test.

How you keep the logic identical

Move the rules, not the structure. Each COBOL paragraph that makes a decision (checks, COMPUTE, IF branches, error codes) becomes a function with the same inputs and outputs.
Match the numbers exactly. COMP-3 becomes Decimal, with the same scale and rounding as COBOL. COMPUTE truncates by default unless ROUNDED is stated. Getting this wrong silently changes amounts.
Keep the same decision order and messages. If COBOL checks A before B and returns the first error, the Python does too.
Prove it with tests. Generate test cases for each branch and boundary of each function and run them (your plan already does this). Where real input and output samples exist, compare against them.
What intentionally changes: the screen flow, the file handling and the state passing. A 3270 screen that shows 7 fields becomes a normal page.

In the tool, that means Stage 4 identifies which paragraphs are business rules, and Stage 6 generates the pure functions first and the routes second.

Next, should we get back to the Stage 1 questions, or do you want to go deeper on any of this first?

Yes we should get back to stahe 1 discussion

Back to Stage 1. Here's the draft so far, kept deliberately simple:

Run it as python stage1.py <codebase_folder> <output_folder>.
It outputs one inventory.json with one entry per file.
It classifies by content only. Folder names and extensions are ignored.
It uses no LLM and no COBOL parser, only regex rules.
It keeps the markdown docs as "documentation".
Each entry would have: path, type, confidence (high, medium or low), line count, the reason it was classified that way (the signature it matched), and a few facts for COBOL files (has EXEC SQL, has EXEC CICS, has COPY, fixed or free format).

Proposed types:
cobol_program, copybook, jcl, jcl_proc, bms_map, assembler, sql_ddl, documentation, data_file, unknown

Question: is this type list right for what you need, or would you add or drop any? For example, CardDemo also has CICS resource definitions and VSAM definition jobs. I'd count those as jcl or unknown unless you want them separate.

Actually we will be developing this tool also as a flask application. But i wnat that application code architecture to be very and not at all overengineered


Updated memory
Updated memory
Here's the simplest structure I'd use, built so each stage is just one more file.

app.py            # Flask routes: all of them, in one file
stage1_inventory.py   # plain function: scan_folder(path) -> list of dicts
(later) stage2_xxx.py, stage3_xxx.py ...
llm.py            # one function: ask_llm(prompt) -> text  (Grok, used from Stage 3)
templates/        # a few plain HTML pages
workspace/        # output of each run: inventory.json, etc.
Rules I'd give Copilot:

Each stage is one file with one main function that takes a folder and returns data. It knows nothing about Flask, so you can also run it from the command line to test it.
app.py only does three things: accept a codebase path, call the stage function, show the result.
Results are saved as plain JSON files in workspace/. There's no database, no classes or layers, and no config system. A later stage reads the previous stage's JSON file, which also gives you resume-after-crash for free.
No background jobs, no login, no extra libraries beyond Flask (and requests for Grok later).
Stage 1 in the web app: one page with a text box for the folder path and a Run button, then a table of files and their types, with a link to download inventory.json.

Question: is the tool running only on your own machine, so the user types a local folder path? That would keep it simplest, since I'd avoid file uploads entirely. Or do you need to upload a zip through the browser?

I dont wnt to restrict the code in quality you can use many libraries and each should not necesaarily only have one file but the code should be easy to follow.

Understood: quality and libraries aren't restricted, and a stage can span several files. The only rule is that the code stays easy to follow.

Revised structure

app.py                  # creates the Flask app, registers routes
routes/                 # one small file per stage page
  stage1.py
stages/
  stage1_inventory/
    scanner.py          # walks the folder, reads files
    classifiers.py      # the content rules, one function per file type
    models.py           # a simple dataclass for one inventory entry
  stage2_.../           # added later, same shape
llm/client.py           # Grok calls (used from Stage 3)
templates/              # HTML pages
workspace/              # JSON output from each stage
tests/                  # one test file per stage
Rules for Copilot

Each stage folder is independent. It takes input and returns data, and it never imports Flask.
classifiers.py has one small function per file type (is_jcl, is_copybook, and so on), so adding a rule means adding one function.
Use a few well-chosen libraries where they save code, for example pytest for tests and chardet for encoding detection. No frameworks beyond Flask.
Clear names, short functions and a docstring on each function. No abstract base classes, plugin systems or config layers.
Stage output is saved as JSON in workspace/. The next stage reads it.
Still open from before: will the tool only run on your machine, so the user types a local folder path, or do you need browser zip upload? Local path is simpler, so I'd default to that unless you say otherwise.

The classifier.py should be very detailed and it should be very accurate. Implement whatever techniques and library you want.

Agreed, accuracy is what Stage 1 is for. Every later stage trusts its labels. Here's the approach I'd have Copilot implement.

1. Normalize before classifying

Detect binary files and EBCDIC (mainframe transfers sometimes arrive undecoded). Try the cp037 and cp1047 code pages. Use charset-normalizer for the rest.
Detect fixed vs free format. Fixed format means columns 1-6 are sequence numbers, column 7 is an indicator and code sits in columns 8-72. Strip those columns and drop comment lines, so a comment saying EXEC SQL never counts as a match.
Normalize line endings and tabs.
2. Score every type, don't stop at the first match

Each type has its own scorer that returns a score plus the evidence behind it. For example:
cobol_program needs IDENTIFICATION DIVISION or PROGRAM-ID plus a PROCEDURE DIVISION.
copybook is level numbers with PIC and no divisions.
jcl is // lines with JOB, EXEC and DD.
bms_map is DFHMSD, DFHMDI and DFHMDF.
sql_ddl is CREATE TABLE.
The highest score wins. If the top two are close, or the top score is low, the file is marked low confidence and the runner-up is recorded.
3. Tricky cases to handle explicitly

A procedure-only COBOL fragment (like your Danish one) gets its own type, cobol_fragment, so it isn't mistaken for a program.
A copybook can be DB2-generated (DECLARE TABLE plus field definitions).
JCL splits into job, proc (has a PROC statement or no JOB card) and include.
HLASM assembler, SQL scripts, CICS resource definitions, sort/utility control cards, and PL/I are separate types. Python, Java and so on are other_source.
A file with several programs concatenated is flagged as having multiple units.
4. Record evidence for every file
Each entry also says why (the lines that matched) and gives a name hint taken from the file name. The file name never decides the type, but copybook names appear in no copybook content, so Stage 2 needs it to resolve COPY ACCTREC to a file.

5. Measure accuracy
We hand-label a small expected.json from the four test codebases, and a pytest test reports accuracy so every rule change is checked against it.

Question: for files the classifier is unsure about, should Stage 1 stay LLM-free and just flag them low confidence for you to review, or may it ask Grok about only those files? I'd keep it LLM-free by default so results are repeatable.

What are wee missing?

Here's what I see missing. The first three are decisions I need from you, the rest I'd add.

Open decisions

Local folder path or zip upload? (I'd default to local path.)
Unsure files: flag only, or ask Grok? (I'd default to flag only.)
Final type list: the ten types from before, plus cobol_fragment, other_source and PL/I?
Gaps in the design

Declared names. Stage 2 has to match COPY ACCTREC or CALL 'TRANPROC' to a file, and the file name can't be trusted. So each entry should record the name the content declares: PROGRAM-ID, the JCL job or proc name, the BMS mapset name, the assembler CSECT name. A copybook has no declared name, so there we use the file name, minus any extension, as a hint.
References and gaps. I said Stage 1 flags missing source but never put it in the output. The simplest version is a light scan for the names after COPY, CALL, EXEC PGM= and EXEC CICS LINK/XCTL, then a list of the names with no matching file. Full analysis stays in Stage 2.
Housekeeping: skip .git and build folders, hash each file (this catches duplicates and lets later stages see what changed), and record file size so huge files get handled sensibly.
Dialect hints per COBOL file. Record CBL/PROCESS cards and any COPY ... REPLACING. This is the cheap hint for the ProLeap-style problem you mentioned.
A summary section. Counts per type and a list of low-confidence files, so you can review Stage 1 in one glance.
Practical gap: I haven't seen real CardDemo or CBSA files yet. Please send those zips, and I'll check the rules against them before writing the Copilot prompt.

Can you answer the three decisions?

What my supervisor wants is we take the entire project. Then we go files by file and create file by ir (the schema of the ir to be discussed and invented based what would be required from it next step. Basically an ir is a structured data about a file that practically facilitates nect steps.) then per file ir should be consolidates in a single ir document. Then again we go to each file we take the file code and its ir data and we to llm which would give us business rules in plain english. Then we consolidate all business rules. Now based on ir and business rules segrate the entire codebase onto small but end to end codebases. So basically we want divide and conquer method on big codebase. We want to break a big codebase with lot of features and funtionalities into small codebases with only functionality such that it could be integrated again when converted. My supervisor just told me "dont focus on conversion focus on feature extraction, on brekaing down th codebase." So help me do that.


Updated memory
Updated memory
That's a clearer goal, and it simplifies things: no conversion, only understanding and splitting. Here's the pipeline as I now understand it.

Inventory: what Stage 1 does, unchanged. It's the file list with types.
Per-file IR (no LLM): structured facts for each file, pulled out with patterns. Examples: declared name, paragraphs with line ranges, COPY/CALL/LINK/XCTL targets, files and DB tables used (read or write), JCL steps (program, files attached), and screens used.
Consolidated IR: one document that joins the per-file IRs. It links each reference to the file that satisfies it, and lists references with no file (the gaps).
Business rules per file (LLM): the code plus its IR go in, plain-English rules come out, with line references.
Consolidated business rules.
Split into slices: each slice is a small end-to-end codebase for one feature.
How the split should work: it should come from the IR, not from the LLM's opinion.

The starting points are the entry points: JCL jobs (batch) and CICS transactions (online).
A slice is everything reachable from an entry point: programs called, copybooks, files, tables, screens.
The LLM then uses the business rules to name each slice and to suggest merging or splitting where entry points clearly belong to one feature.
The hard part is shared things: a utility program, a copybook, or a table used by many slices. I'd put these in a "shared" list and have each slice's manifest record them as dependencies and as interfaces. That is what lets the pieces be rejoined later: two slices that touch the same table are connected through that table.

Changes to Stage 1: it stays as is, but the classifier now also needs to find the entry points (JCL job names and CICS transaction definitions). That's a small addition.

Question: in your real projects, is a feature usually one entry point (one job or one transaction), or does one feature span several, such as a screen transaction plus a nightly job that share a table? That decides whether a slice defaults to one entry point or to a group.

I dont know that, because i dont understand the cobol code

That's fine. I don't need you to know it, because the tool can find out from the code itself. Here's a default rule that works either way.

Default slicing rule

Start with one slice per entry point (each JCL job, each CICS transaction). This is always safe and small.
Then merge slices that write to the same file or table. Two entry points that update the same data are almost certainly the same feature, such as a screen that adds an account and a nightly job that reads those accounts.
A utility program or copybook used by many slices doesn't cause merging. It goes in the shared list.
The LLM, using the business rules, only names each slice and flags suspicious ones (for example "these two look like one feature"). It never decides the file membership, so the result is repeatable.
Slice sizes can be adjusted later by tweaking the merge rule, so we don't have to get it perfect now.

I'll go with these defaults for Stage 1 unless you say otherwise:

The tool reads a local folder path, with no zip upload.
Unsure files are flagged low confidence and never sent to the LLM.
The type list is the ten earlier types plus cobol_fragment, other_source and PL/I, and entry points are recorded.
Next step: please send the CardDemo and CBSA zips so I can check the classification rules against real files. Otherwise I can write the Copilot prompt now from the banking repo and your Danish sample. Which do you prefer?

What if there are no jcl or cics file in the codebase

That's a realistic case, because the JCL and CICS resource definitions are often the files that don't get shared. The fallback is to find entry points from the programs themselves.

Entry-point rules, in order

JCL job or CICS transaction definition, if present. This is the best source because it states the real entry points.
Programs nobody calls. From the CALL, LINK and XCTL references we build a call graph, and any program with no inbound call is a root. These are the starting points of features.
Signs of a main program. A program that ends with STOP RUN, or whose PROCEDURE DIVISION takes no USING parameters, is probably a top-level program. A program with a LINKAGE SECTION and PROCEDURE DIVISION USING is usually a subprogram called by another.
Signs of an online program. If a program contains EXEC CICS commands such as RECEIVE MAP, SEND MAP or RETURN TRANSID, treat it as an online entry point even without CICS definitions. Its MAP name links it to its screen.
Edge cases

A group of programs that call each other in a loop count as one unit.
If every program is called by something missing, the tool marks the entry points as assumed and lists the missing callers as gaps, so a reviewer can confirm.
Slices are then built the same way as before: one per entry point, merged when they write to the same data.
So missing JCL or CICS reduces confidence, not functionality. The tool records "entry point inferred from call graph" in the output.

Do you want to go ahead with the defaults and have me write the Stage 1 Copilot prompt now? If you can send the CardDemo and CBSA zips first, I'll test the rules against them before finalizing.

How do we develop such tool incrementally such taht each increment is testable. Design a development plan

Here's the plan. Every increment has an output you can inspect and a pass check, and nothing starts until the previous one passes.

#	Increment	Pass check
0	Flask app with one page: type a folder path, see "N files found"	Page loads and the count matches the folder
1	Reader: encoding detection, fixed vs free format, comment stripping	Unit tests on small snippets, including EBCDIC and CRLF
2	Classifier with evidence and confidence	Accuracy against a hand-labelled expected.json (banking repo, then your Danish sample, then CardDemo and CBSA)
3	Declared names, references and gap list (the rest of Stage 1)	Banking repo reports exactly these gaps: ACCTREC, SQLCA, ERRHDLR, TRANREC, TRANPROC
4	Per-file IR, one file type at a time: COBOL program, then copybook, JCL, BMS	Each IR hand-checked on one or two real files. The schema grows only when the next step needs a field
5	Consolidated IR: links, call graph, entry points	Graph on the banking repo matches the real flow: DAILY → programs
6	Business rules per file (Grok)	On a small program such as INTCALC, the rules match a list you write by hand. Line references must point to real lines
7	Consolidated business rules	Every rule traces back to a file and lines
8	Slicing	Each file belongs to a slice or the shared list, and no slice depends on a file outside itself and the shared list
9	Slice export: copy each slice's files into a folder with a manifest	The manifest lists every file, every shared dependency and every gap
Rules for every increment

Each stage reads the previous stage's JSON from workspace/, so it can be run and tested alone.
Stages 6 and 7 are the only ones that use the LLM. Stages 1-5 and 8-9 are repeatable, so a failing test means a code bug.
After each increment, run all test codebases, commit, and review the output before moving on.
Increments 0-3 make up Stage 1.
Shall I write the Copilot prompt for increments 0 to 2 now? Please send the CardDemo and CBSA zips first if you can, so I can check the rules against them.

We will doscuss the ir schema when devloping that increment. For now lets work on increment 0. Do you need to ask any questions from me regarding that before you create the prompt for copilot?

No blocking questions, because Increment 0 is small. I'm assuming Windows, Python 3.10+ and a virtual environment, and that the app runs only on your machine and takes a local folder path. If any of that is wrong, tell me. Here's the prompt for Copilot:

You are a programmer who writes exactly what is specified below. Do not add features, 
files, classes, config, logging, or libraries that are not listed. If something is 
unclear, choose the simplest option and add nothing extra.

GOAL
A small Flask app with one page. The user types a local folder path, clicks Run, and 
sees how many files are in that folder (recursively) and a list of their relative paths.

PROJECT LAYOUT (create exactly these files)
  app.py
  requirements.txt
  stages/__init__.py
  stages/stage1_inventory/__init__.py
  stages/stage1_inventory/scanner.py
  templates/index.html
  tests/test_scanner.py

requirements.txt
  flask
  pytest

stages/stage1_inventory/scanner.py
  One function:
    def list_files(folder: str) -> list[str]
  Behavior:
  - If folder is not an existing directory, raise ValueError with a short message 
    "Folder not found: <folder>".
  - Walk the folder recursively with os.walk.
  - Skip directories named: .git, .svn, node_modules, __pycache__ (do not enter them).
  - Do NOT open or read any file. Only collect paths.
  - Return the paths relative to `folder`, using forward slashes, sorted alphabetically.
  - Add a one-line docstring.
  - This module must not import Flask.

app.py
  - Create a Flask app.
  - One route "/" accepting GET and POST.
  - GET: render index.html with no result.
  - POST: read form field "folder_path". Strip whitespace and strip surrounding 
    double quotes (Windows "Copy as path" adds them). Call list_files.
    - On success: render index.html with the folder path, the file count, and the list.
    - On ValueError: render index.html with the error message.
  - Run with app.run(debug=True) when executed directly.

templates/index.html
  - Plain HTML, no CSS framework, no JavaScript.
  - Title "Legacy Modernization Tool - Stage 1".
  - A form (method POST) with a text input named folder_path (wide, keeps the 
    submitted value) and a Run button.
  - If there is an error, show it in red text above the form results.
  - If there is a result, show "N files found in <folder>" and below it a simple 
    HTML table with one column "File" listing every relative path.

tests/test_scanner.py
  Use pytest and the tmp_path fixture. Tests:
  1. Nested files are all found, and returned paths are relative with forward slashes.
  2. Files inside a ".git" folder are not returned.
  3. A folder path that does not exist raises ValueError.
  4. Result is sorted.

DO NOT
  - add a database, classes, blueprints, config files, environment variables, 
    logging, or any other library.
  - read file contents.
  - create any file not listed above.

HOW I WILL RUN IT (Windows PowerShell)
  python -m venv .venv
  .venv\Scripts\Activate.ps1
  pip install -r requirements.txt
  python -m pytest
  python app.py
How to check the increment

pytest passes all 4 tests.
Run python app.py, open http://127.0.0.1:5000, and enter the banking repo path. You should see 14 files, with .md, .cbl and .jcl all listed.
Enter a wrong path and confirm the red error message appears.
Paste a path with quotes around it and confirm it still works.
Tell me what happens, and we'll move to Increment 1.

Where would i enyer the path?

In the text box on the web page. Once the app is running, open http://127.0.0.1:5000 in your browser. You'll see the page Copilot built, with a wide text input and a Run button.

Type or paste the full path to the folder, for example:

C:\Users\Shamoil\Downloads\banking-cobol-jcl-db2-main

Then click Run. You can paste the path with quotes from Windows' "Copy as path", since the app strips them.

The folder has to exist on the same machine where the app runs, which is your laptop.

Implemented the requested Flask folder-inventory app:

app.py serves one GET/POST page. On POST, it trims the submitted path and surrounding double quotes, then displays the result or a validation error.
scanner.py recursively collects sorted relative file paths, using forward slashes. It skips .git, .svn, node_modules, and __pycache__, and does not read file contents.
index.html provides the form and renders the file count and paths in a table.
requirements.txt, package initializer files, and test_scanner.py were added.
The tests cover nested paths, .git exclusion, missing folders, and sorting. **The test run was interrupted, so they have not been verified.** No JSON output was implemented; results are shown on the webpage.

This the summary of increment zero. Bow we move to increment 1. Do you have any doubts before we do that

One thing first: Copilot says the test run was interrupted, so Increment 0 isn't verified yet. Before we move on, please run these in PowerShell inside the project folder:

python -m pytest
python app.py
Check that all 4 tests pass and that the banking repo shows 14 files in the browser. If anything fails, paste me the error.

Doubts for Increment 1: none that block me. I'll assume these defaults for the reader:

It handles ASCII/UTF-8 text, EBCDIC files that were never converted, and binary files (which it marks as binary rather than reading).
It detects fixed or free format per file.
It strips sequence numbers and comment lines, but keeps the original line numbers so later stages can point to real lines.
It returns the original text and the cleaned text for each file.
It reads files with Python's standard library plus charset-normalizer.
Reply with the test result, and I'll write the Increment 1 prompt.

lets move to increment 1

Here's the Increment 1 prompt. It also adds a few columns to the web table so you can see the reader's results.

You are a programmer who writes exactly what is specified below. Do not add features,
files, classes, config, logging, or libraries that are not listed. If something is
unclear, choose the simplest option and add nothing extra. Keep the code easy to read:
short functions, clear names, a one-line docstring on each function.

GOAL
Add a "reader" to Stage 1. Given a file path, it detects the encoding, line ending style
and source format, and returns the raw lines plus the cleaned "code lines" (comments and
column areas removed) with original line numbers kept. It must work on any text file,
whatever its type. It must not know anything about COBOL/JCL file types.

CHANGES
  NEW   stages/stage1_inventory/models.py
  NEW   stages/stage1_inventory/reader.py
  NEW   tests/test_reader.py
  EDIT  requirements.txt      (add: charset-normalizer)
  EDIT  app.py                (call the reader for each file, pass results to template)
  EDIT  templates/index.html  (add table columns)
Do not touch scanner.py or test_scanner.py.

models.py
  A dataclass FileContent with these fields:
    path: str
    kind: str                 # "text" | "binary" | "too_large"
    encoding: str | None      # "utf-8" | "cp037" | other detected name | None
    line_ending: str          # "LF" | "CRLF" | "CR" | "mixed" | "none"
    source_format: str | None # "fixed" | "free" | None (None when not text)
    raw_lines: list[str]      # decoded lines, tabs expanded, no line terminators
    code_lines: list[tuple[int, str]]  # (original 1-based line number, cleaned text)

reader.py
  One public function: read_file(path: str) -> FileContent
  Use only the standard library plus charset-normalizer. Steps, in this order:

  1. If file size > 10 MB: return kind "too_large", encoding None, line_ending "none",
     source_format None, empty lists. Do not read it.

  2. Read all bytes. If b"\x00" is in the first 8192 bytes: return kind "binary"
     (same empty values as above).

  3. Decode:
     a. Try utf-8 (use "utf-8-sig" so a BOM is removed). If it works, encoding "utf-8".
     b. Else check for EBCDIC: decode the bytes with "cp037"; it is EBCDIC if the byte 0x40
        makes up at least 10% of all bytes AND at least 98% of the decoded characters are
        printable or whitespace. Then encoding is "cp037". Replace the character "\x85" with "\n".
        If the decoded text has no "\n" and its length is a multiple of 80, split it into
        records of 80 characters each (these become the lines, line_ending "none").
     c. Else use charset_normalizer.from_bytes(data).best(); use its encoding name.
        If it returns None, decode as latin-1 and use encoding "latin-1".

  4. Line ending: before splitting, count "\r\n", lone "\n" and lone "\r" in the decoded
     text. Only one kind present -> "CRLF" / "LF" / "CR". More than one -> "mixed".
     None present -> "none". (For the EBCDIC 80-char records case it is "none".)

  5. Split into lines (str.splitlines, no terminators kept; for the 80-char records use the
     records). Expand tabs with line.expandtabs(8). This is raw_lines. An empty file gives
     empty lists, kind "text", line_ending "none", source_format "free".

  6. Detect source_format:
     - "free" if one of the first 50 lines matches, case-insensitive,
       regex  ^\s*>>\s*SOURCE\s+FORMAT\s+(IS\s+)?FREE
     - Otherwise look at the non-blank lines that are at least 7 characters long. A line
       "looks fixed" if its first 6 characters match ^[ 0-9A-Za-z]{6}$ AND its 7th
       character is one of: space * / - D d
       If there are at least 3 such lines and at least 80% of them look fixed -> "fixed".
       Otherwise -> "free".

  7. Build code_lines (keep original 1-based line numbers; always skip blank lines):
     - fixed: if the 7th character is * or /, skip the line (comment). Otherwise take
       characters from position 8 to 72 (line[7:72]) and rstrip it. Lines shorter than
       7 characters are skipped.
     - free: rstrip the line. Skip it if its lstripped text starts with "*>" or "//*".
       If it contains " *>", cut the line at that point and rstrip it again.

  Return the FileContent.

app.py
  After list_files, for each relative path call read_file(os.path.join(folder, rel_path)).
  Pass the template, for each file: the relative path, kind, encoding, line_ending,
  source_format, len(raw_lines), len(code_lines). Keep the existing error handling.

index.html
  Extend the table columns to: File | Kind | Encoding | Line ending | Format | Lines | Code lines.
  Show "-" for values that are None. No other changes.

tests/test_reader.py  (pytest, tmp_path; write files with write_bytes)
  1. UTF-8 file with LF endings: kind text, encoding utf-8, line_ending LF.
  2. File with CRLF endings -> CRLF. File with a mix of CRLF and LF -> mixed.
  3. File with a NUL byte -> kind binary, empty lists.
  4. EBCDIC: take 3 lines of COBOL text, pad each to 80 characters, join with no
     newline, encode with cp037. Result: encoding cp037, 3 raw_lines, line_ending none,
     and raw_lines[0] starts with the original first line.
  5. Fixed format with sequence numbers. Use these 4 lines:
       "000100 IDENTIFICATION DIVISION.                                         00010000"
       "000200* THIS IS A COMMENT                                               00020000"
       "000300 PROGRAM-ID. TESTPGM.                                             00030000"
       "000400     STOP RUN.                                                    00040000"
     Expect source_format fixed, code_lines have 3 entries, the comment line is gone,
     line numbers are 1, 3, 4, text starts at column 8 (e.g. "IDENTIFICATION DIVISION."),
     and the sequence numbers at the end (columns 73-80) are not in the text.
     (Use at least 3 qualifying lines: add more similar lines if needed.)
  6. Fixed format without sequence numbers: lines that begin with 7 spaces then code.
     Expect source_format fixed and code_lines without the 7 leading spaces.
  7. JCL file:
       "//JOB1 JOB (ACCT),'TEST'"
       "//* COMMENT"
       "//STEP1 EXEC PGM=MYPROG"
     Expect source_format free, the "//*" line is skipped, line numbers 1 and 3.
  8. Free COBOL with a "*> comment" line and a line ending in "   *> note": the comment
     line is skipped and the trailing note is removed.
  9. A markdown file with prose lines -> source_format free.
  10. An empty file -> kind text, no lines.

DO NOT
  - add classes other than FileContent, abstract bases, config files, logging, or any
    library other than charset-normalizer.
  - guess file types or look at file names or extensions.
  - join continuation lines or change anything not listed above.

HOW I WILL RUN IT (Windows PowerShell)
  pip install -r requirements.txt
  python -m pytest
  python app.py
How to check Increment 1

Make sure all tests pass, the old 4 and the new 10.
Run it on the banking repo. The .cbl files should show Format = fixed, and the .jcl and .md files should show free. Encoding should be utf-8 everywhere.
Tell me what the Lines and Code lines columns say for COBOL/INTCALC.cbl, and I'll check them against the real file.
Please also confirm that Increment 0's tests passed. Last time Copilot said the run was interrupted.

Discuss increment 2 with me before prompt

Here's my picture of Increment 2, so we can fix anything before I write the prompt.

What it does: it takes the reader's output for one file and returns a type, a confidence, the evidence (the lines that matched), and the runner-up type. It never looks at file names, extensions or folders.

How it decides:

There's one small scoring function per type. Each returns a score and its evidence.
The highest score wins. If the top two are close or the top score is weak, confidence is low and the runner-up is kept.
The matching runs on code_lines, so a comment mentioning EXEC SQL doesn't count.
A file that is binary, too large or empty gets a fixed answer (binary, too_large, empty) without scoring.
Types and the main signature for each:

cobol_program: PROGRAM-ID plus PROCEDURE DIVISION.
cobol_fragment: a PROCEDURE DIVISION or paragraphs but no PROGRAM-ID.
copybook: level numbers with PIC, and no divisions.
jcl and jcl_proc: // lines with JOB (job) or PROC and no JOB (proc).
bms_map: DFHMSD, DFHMDI, DFHMDF.
sql_ddl: CREATE TABLE, CREATE INDEX and similar.
assembler: CSECT, DSECT, USING.
pli: PROC OPTIONS(MAIN), DCL.
documentation: prose with no code signatures.
other_source: for example Python or Java.
unknown: nothing scores well.
Output: for now, shown in the web table and tested with pytest, with no JSON file yet. Entry points, declared names and the gap list belong to Increment 3.

How we test accuracy: an expected.json maps each test file to its correct type, and one pytest checks every file against it. You said you don't read COBOL, so I'd draft the labels for each test codebase after reading it myself, and you'd only spot-check.

Question: do you have the CardDemo and CBSA zips yet? The rules need to see real files with CICS, BMS and copybooks, and the banking repo has none of those.

Remove the need for expected.json for now. We will take the tools word for it. And why arent we creating ay json right now nd when wil we make them

Fair on expected.json. Instead, each type gets a small test with a made-up snippet (a few lines of fake JCL, COBOL and so on), so the tests check the rules and not your real files. Real-file accuracy is then something you judge by reading the web table. The risk is that a wrong label on a real file goes unnoticed unless you look at it, so I'd glance at the table after each run.

Why there's no JSON yet: only because I was keeping each increment small. Before Increment 2 there was nothing worth saving, since the reader's output is just raw material. That's a weak reason now, so I'd change it.

My suggestion: write workspace/inventory.json starting in Increment 2, because the classifier's result is the first real output of Stage 1. It would hold only summary fields for each file: path, type, confidence, evidence, runner-up, encoding, line ending, format, line counts. The raw and cleaned lines stay out, since they're big and the next stages can re-read the files. Increment 3 then adds declared names, references and gaps to the same file.

Do you want the JSON written from Increment 2, or kept for Increment 3?

Okay crete the prompt


Updated memory
Updated memory
Here's the Increment 2 prompt. I made three choices: the SQL type is named sql (not sql_ddl) since it covers any standalone SQL file; inventory.json is written from this increment, as we agreed; and a markdown file containing code snippets is labelled documentation before any other scoring, so JCL or COBOL samples inside READMEs don't fool the classifier.

You are a programmer who writes exactly what is specified below. Do not add features,
files, classes, config, logging, or libraries that are not listed. If something is
unclear, choose the simplest option and add nothing extra. Keep the code easy to read:
short functions, clear names, a one-line docstring on each function.

GOAL
Add a classifier to Stage 1. For each file, using only its content (never its name,
extension or folder), decide its type, a confidence, and the evidence for the decision.
Save the results to workspace/inventory.json and show them in the web page.

CHANGES
  EDIT  stages/stage1_inventory/models.py      (add a dataclass)
  NEW   stages/stage1_inventory/scorers.py     (one scoring function per file type)
  NEW   stages/stage1_inventory/classifier.py  (decision logic)
  NEW   stages/stage1_inventory/inventory.py   (builds and saves the inventory)
  NEW   tests/test_classifier.py
  EDIT  app.py
  EDIT  templates/index.html
Do not change scanner.py, reader.py or their tests. No new libraries.

models.py
  Add dataclass Classification with fields:
    file_type: str
    confidence: str          # "high" | "medium" | "low"
    evidence: list[str]      # e.g. "line 12: PROGRAM-ID. TESTPGM."
    runner_up: str | None
    scores: dict[str, int]   # only types with score > 0

scorers.py
  Input to every scorer: code_lines, a list of (line_number, text) from FileContent.
  Every scorer returns (score: int, evidence: list[str]).
  Evidence strings look like  f"line {n}: {text.strip()[:80]}"  and each scorer returns at
  most 5 of them (the first matches).
  Compile all regexes once as module constants. Unless said otherwise use re.IGNORECASE and
  re.search on each line's text. A helper  find(code_lines, regex) -> list[(n, text)]  returns
  the matching lines; use it in all scorers.
  Define SCORERS = {type_name: scorer_function} for exactly these types:
  cobol_program, cobol_fragment, copybook, jcl, jcl_proc, bms_map, assembler, pli, sql,
  other_source, documentation.

  cobol_program
    has_id  = any line matching  ^\s*PROGRAM-ID\b
    If not has_id: return (0, []).
    score = 4
          + 4 if any line matches ^\s*PROCEDURE\s+DIVISION
          + 2 if any line matches ^\s*(IDENTIFICATION|ID)\s+DIVISION
          + 1 if any line matches ^\s*DATA\s+DIVISION
          + 1 if any line matches ^\s*ENVIRONMENT\s+DIVISION
    If there are 2 or more PROGRAM-ID lines, add the evidence string
    "N PROGRAM-ID lines (multiple programs)".

  cobol_fragment
    If any line matches ^\s*PROGRAM-ID\b: return (0, []).
    score = 4 if any line matches ^\s*PROCEDURE\s+DIVISION
    verb_lines = lines matching
      ^\s*(MOVE|PERFORM|IF|EVALUATE|COMPUTE|ADD|SUBTRACT|MULTIPLY|DIVIDE|DISPLAY|ACCEPT|READ|WRITE|REWRITE|OPEN|CLOSE|CALL|GO\s+TO|STOP\s+RUN|GOBACK|INITIALIZE|STRING|UNSTRING|INSPECT|EXEC\s+SQL|EXEC\s+CICS|END-IF|END-EVALUATE|END-PERFORM)(?=\s|\.|$)
      but ignore any line whose stripped text ends with ":" or "{" or ";".
    score += min(number of verb_lines, 10)

  copybook
    If any line matches ^\s*PROGRAM-ID\b or ^\s*PROCEDURE\s+DIVISION: return (0, []).
    level_lines = lines matching
      ^\s*(0[1-9]|[1-4][0-9]|66|77|88)\s+([A-Z0-9][A-Z0-9-]*|FILLER)\b
    pic_lines = lines matching \b(PIC|PICTURE)\b
    If len(level_lines) < 2: return (0, []).
    score = min(len(level_lines), 8) + (2 if pic_lines else 0)
          + (3 if any line matches EXEC\s+SQL\s+DECLARE\s+\S+\s+TABLE)

  jcl
    slash_lines = lines starting with "//"
    job_lines = lines matching ^//\S*\s+JOB\b
    If no job_lines or len(slash_lines) < 2: return (0, []).
    exec_lines = ^//\S*\s+EXEC\b ;  dd_lines = ^//\S*\s+DD\b
    score = 5 + (3 if exec_lines else 0) + min(len(dd_lines), 4)

  jcl_proc
    If any line matches ^//\S*\s+JOB\b: return (0, []).
    slash_lines as above. If len(slash_lines) < 2 or len(slash_lines) < 50% of len(code_lines):
    return (0, []).
    score = (5 if any line matches ^//\S*\s+PROC\b) + (3 if any EXEC line)
          + min(number of DD lines, 4)     (EXEC and DD regexes as in jcl)

  bms_map
    score = (5 if any line matches \bDFHMSD\b) + (3 if any matches \bDFHMDI\b)
          + min(number of lines matching \bDFHMDF\b, 5)

  assembler
    If any line matches \bDFHMSD\b: return (0, []).
    score = (4 if any line matches (?:^|\s)(CSECT|DSECT|RSECT)\b)
          + min(number of lines matching ^\S*\s+(DS|DC)\s+\d*[CXFHPAZDEBS], 4)
          + (2 if any line matches \sUSING\s+(\*|\w+,\s*\d+))
          + min(number of lines matching (?:^|\s)(BALR|BASR|STM|LM|MVC|CLC|LTR|LR|BNZ|BZ|BNE|BE)\s, 4)

  pli
    score = (6 if any line matches OPTIONS\s*\(\s*MAIN)
          + min(number of lines matching ^\s*DCL\s, 5)
          + (3 if any line matches ^\s*\S+:\s*(PROC|PROCEDURE)\b)

  sql
    If any line matches EXEC\s+SQL: return (0, []).
    ddl_lines = lines matching
      ^\s*(CREATE|ALTER|DROP)\s+(OR\s+REPLACE\s+)?(TABLE|INDEX|VIEW|TABLESPACE|DATABASE|STOGROUP|SEQUENCE|ALIAS|SCHEMA|PROCEDURE|TRIGGER|UNIQUE)\b
    other_lines = lines matching ^\s*(GRANT|COMMENT\s+ON|COMMIT)\b
    semicolon_lines = lines whose stripped text ends with ";"
    dml_lines = lines matching ^\s*(SELECT|INSERT\s+INTO|UPDATE|DELETE\s+FROM)\b
    score = min(3 * len(ddl_lines), 12) + min(len(other_lines), 3)
          + (min(len(dml_lines), 4) if len(semicolon_lines) >= 2 else 0)

  other_source   (case-SENSITIVE regexes; no re.IGNORECASE)
    patterns, as (language, regex) pairs:
      python  ^\s*def\s+\w+\(.*\)\s*(->.*)?:\s*$
      python  ^\s*class\s+\w+.*:\s*$
      python  ^\s*(import\s+\w+|from\s+[\w.]+\s+import\s)
      java    ^\s*(public|private|protected)\s+(static\s+)?(class|interface|enum|void|[\w<>\[\]]+)\s+\w+
      java    ^\s*package\s+[\w.]+;
      java    ^\s*import\s+[\w.*]+;
      csharp  ^\s*using\s+[\w.]+;
      js      ^\s*(const|let|var)\s+\w+\s*=
      js      ^\s*function\s+\w+\s*\(
      c       ^\s*#include\s*[<"]
      shell   ^#!/
      xml     ^\s*<\?xml
    score = min(2 * number of (line, pattern) matches, 10)
    Evidence strings are prefixed with the language: "python line 3: import os".

  documentation
    counts (case-sensitive), using a helper  markdown_counts(code_lines) -> dict  with keys:
      headings  lines matching ^#{1,6}\s+\S
      fences    lines starting with ```
      bullets   lines matching ^\s*[-*+]\s+\S
      tables    lines matching ^\|.*\|\s*$
      links     lines matching \[[^\]]+\]\([^)]+\)
    score = min(2*headings, 6) + min(2*fences, 6) + min(bullets, 4) + min(tables, 3) + min(links, 3)
    Also define  looks_like_markdown(code_lines) -> bool :
      fences >= 2   OR   (headings >= 2 AND bullets + tables + links >= 2)

classifier.py
  Function 1:  decide_type(scores: dict[str, int]) -> tuple[str, str, str | None]
    returns (file_type, confidence, runner_up).
    - Sort items by (-score, name). top = first, second = next (score 0 if none).
    - If top score < 5: file_type "unknown", confidence "low",
      runner_up = top's name if top score > 0 else None.
    - Else file_type = top name, runner_up = second's name if second score > 0 else None, and
      margin = top score - second score:
        "high"   if top >= 8 and margin >= 4
        "medium" if top >= 5 and margin >= 2
        "low"    otherwise.
  Function 2:  classify(content: FileContent) -> Classification
    1. kind "too_large" -> file_type "too_large"; kind "binary" -> file_type "binary";
       both with confidence "high", evidence ["kind: <kind>"], runner_up None, scores {}.
    2. If every line in raw_lines is blank (or raw_lines is empty) -> file_type "empty",
       confidence "high", evidence [], runner_up None, scores {}.
    3. If looks_like_markdown(content.code_lines): file_type "documentation",
       confidence "high", evidence from the documentation scorer, runner_up None,
       scores {"documentation": its score}. Do not run the other scorers.
    4. Otherwise run every scorer in SCORERS on content.code_lines, keep a dict of scores,
       call decide_type, and set evidence to the evidence list of the top-scoring type
       (empty list if all scores are 0). scores in the result = only types with score > 0.

inventory.py
  Function 1:  build_inventory(folder: str) -> dict
    - files = list_files(folder)  (from scanner.py)
    - For each relative path: read_file(os.path.join(folder, rel)), classify(content),
      os.path.getsize for size.
    - Each file entry is a dict with keys: path, type, confidence, evidence, runner_up,
      scores, kind, encoding, line_ending, source_format, size_bytes, line_count
      (len(raw_lines)), code_line_count (len(code_lines)).
    - Return {"source_folder": folder,
              "summary": {"total_files": N,
                          "by_type": {type: count, ...},
                          "low_confidence": [paths with confidence "low"]},
              "files": [entries sorted by path]}
  Function 2:  write_inventory(inventory: dict, workspace_dir: str) -> str
    - Create workspace_dir if needed, write inventory.json (json.dump, indent=2,
      ensure_ascii=False, utf-8), return the file path.

app.py
  - Define WORKSPACE_DIR = the "workspace" folder next to app.py.
  - On POST: after validating the folder path (keep the existing quote stripping and error
    handling), call build_inventory(folder), then write_inventory. Pass the inventory to the template.
  - Add route GET /inventory.json that returns workspace/inventory.json using send_file,
    or the text "No inventory yet" with status 404 if the file does not exist.
  - Remove the old per-file reader loop (build_inventory replaces it).

templates/index.html
  - Keep the form and error display.
  - Under a result show: "N files found in <folder>", then one line listing the counts per
    type (for example "cobol_program: 4, jcl: 2, documentation: 8"), and a link
    "Download inventory.json" pointing to /inventory.json.
  - Table columns: File | Type | Confidence | Runner-up | Evidence | Encoding | Format | Lines.
    Evidence cell: the evidence strings separated by <br>, in a <small> tag.
    Rows with confidence "low" get style="background:#fff3cd". Show "-" for None values.

tests/test_classifier.py  (pytest, tmp_path)
  Helper: write a file with write_text, call read_file then classify.
  Put each test snippet's lines in a list and join with "\n".
  A. cobol_program (expect type cobol_program, confidence high), 7 leading spaces on every line:
       IDENTIFICATION DIVISION.
       PROGRAM-ID. TESTPGM.
       ENVIRONMENT DIVISION.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01  WS-A  PIC 9(3).
       PROCEDURE DIVISION.
           MOVE 1 TO WS-A.
           STOP RUN.
  B. cobol_fragment (expect cobol_fragment), 7 leading spaces on every line:
       PROCEDURE DIVISION.
       MAIN-PARA.
           PERFORM INIT-PARA.
           MOVE 1 TO WS-A.
           IF WS-A = 1
               DISPLAY 'ONE'
           END-IF.
           STOP RUN.
  C. copybook (expect copybook), 7 leading spaces on every line:
       01  ACCT-RECORD.
           05  ACCT-NUMBER     PIC X(10).
           05  ACCT-BALANCE    PIC S9(9)V99 COMP-3.
           05  ACCT-STATUS     PIC X(1).
  D. jcl (expect jcl, high):
       //DAILYJOB JOB (ACCT),'DAILY RUN',CLASS=A
       //STEP01   EXEC PGM=ACCTMSTR
       //INFILE   DD DSN=BANK.INPUT,DISP=SHR
       //OUTFILE  DD DSN=BANK.OUTPUT,DISP=(NEW,CATLG)
       //SYSOUT   DD SYSOUT=*
  E. jcl_proc (expect jcl_proc):
       //MYPROC   PROC
       //STEP1    EXEC PGM=IEFBR14
       //DD1      DD DSN=&HLQ..DATA,DISP=SHR
  F. bms_map (expect bms_map):
       MAPSET1  DFHMSD TYPE=&SYSPARM,MODE=INOUT,LANG=COBOL
       MAP1     DFHMDI SIZE=(24,80)
       FIELD1   DFHMDF POS=(1,1),LENGTH=10
                DFHMSD TYPE=FINAL
     (the last line is 9 spaces then DFHMSD ...)
  G. assembler (expect assembler):
       MYPROG   CSECT
                USING *,12
                STM   14,12,12(13)
                LR    12,15
                MVC   WORK(8),=CL8'HELLO'
       WORK     DS    CL8
                END
     (continuation lines start with 9 spaces)
  H. pli (expect pli):
       MYPROG: PROC OPTIONS(MAIN);
         DCL X FIXED BIN(31);
         DCL Y CHAR(10);
         X = 1;
       END MYPROG;
  I. sql (expect sql):
       CREATE TABLE ACCOUNT (
           ACCT_NO CHAR(10) NOT NULL,
           BALANCE DECIMAL(11,2)
       );
       CREATE INDEX IX1 ON ACCOUNT (ACCT_NO);
       GRANT SELECT ON ACCOUNT TO PUBLIC;
  J. other_source (expect other_source):
       import os
       from pathlib import Path

       def main():
           print('hi')

       class Foo:
           pass
  K. documentation: a markdown file with "# Title", a blank line, "- item one", "- item two",
     then a fenced block (``` line, the three JCL lines of test D, ``` line).
     Expect documentation (not jcl).
  L. unknown: three plain English sentences with no code. Expect unknown, confidence low.
  M. empty file -> "empty". File containing bytes b"abc\x00def" -> "binary".
  N. A COBOL program (as test A plus one more line "      * USES DFHMSD DFHMDI DFHMDF" inserted
     after the first line, six spaces then a star at column 7) must still be cobol_program,
     because comment lines are ignored.
  O. A COBOL program (as test A) with an added line "           EXEC SQL COMMIT END-EXEC."
     before STOP RUN must still be cobol_program (the sql type must score 0).
  P. decide_type unit tests (no files):
       {"jcl": 10, "cobol_program": 1}  -> ("jcl", "high", "cobol_program")
       {"jcl": 6, "copybook": 5}        -> ("jcl", "low", "copybook")
       {"jcl": 3}                        -> ("unknown", "low", "jcl")
       {}                                -> ("unknown", "low", None)
  Q. build_inventory + write_inventory on a tmp folder containing the files from tests A and D
     (named anything): the JSON file exists, loads, has 2 entries in "files", and
     summary.total_files == 2.

DO NOT
  - look at file names, extensions or folder names to decide a type.
  - call any LLM or add any library, or add types beyond those listed.
  - add classes other than the dataclass, abstract bases, config or logging.
  - store the raw or cleaned lines in the JSON.

HOW I WILL RUN IT (Windows PowerShell)
  python -m pytest
  python app.py
How to check the increment

All tests pass (the earlier ones plus the new ones).
Run the banking repo. COBOL/*.cbl should come out as cobol_program, JCL/*.jcl as jcl, and the .md files as documentation. Please tell me every row where the type or confidence looks off.
Open workspace/inventory.json and confirm it has a summary and one entry per file.
One known limit: a SQL script with only SELECT/INSERT statements and no semicolons will come out as unknown. We can fix that when it shows up in real files.

Discus incrememt 3 what it would do, what input it would take, how it would work and waht output would it provide

Increment 3 completes Stage 1. Increment 2 says what each file is, and this one says what each file is called, what it refers to, and what's missing.

What it does

Declared names: it records the name each file declares for itself: PROGRAM-ID for programs, the job name for JCL, the proc name for procs, the mapset and map names for BMS, CSECT labels for assembler.
References: it finds what each file points to:
COPY and EXEC SQL INCLUDE (copybooks)
CALL 'X', and CALL with a variable, marked dynamic because it can't be resolved
EXEC CICS LINK/XCTL PROGRAM('X'), SEND/RECEIVE MAP, RETURN TRANSID
JCL EXEC PGM=X, EXEC procname and INCLUDE MEMBER=
Resolution and gaps: each reference is matched to a declared name. Matches are recorded. IBM-supplied names (SQLCA, IEFBR14, SORT, IDCAMS and similar) are marked system. Anything else is a gap.
Entry points: every JCL job is an entry point. Programs that use RETURN TRANSID or RECEIVE MAP are online entry points, and programs nobody calls are root programs. The second and third kinds are marked inferred.
Housekeeping: duplicate declared names and a content hash for each file.
Input: the inventory from Increment 2 plus the folder. The files are re-read with the reader, since the cleaned lines aren't stored.

Output: the same inventory.json, extended:

Each file gains declared_name and a list of references (kind, name, line, and resolved to a file, system, dynamic or nothing).
The top level gains gaps, entry_points and duplicates.
The web page gets a gaps list and an entry points list.
Left for the IR (Increment 4): DB2 tables, files read or written, and paragraph-level structure. They need the fuller schema.

What I'd expect on the banking repo:

gaps: ACCTREC, TRANREC, ERRHDLR, and TRANPROC (called from JCL)
SQLCA: system
entry points: the JCL jobs, plus any program nobody calls
Correction: I earlier listed SQLCA as a gap, but IBM supplies it, so it should count as system.

Question: copybook content never contains its own name, so the only way to match COPY ACCTREC to a file is the file name without folder or extension (ACCTREC.cpy or just ACCTREC). This is the one place where we use a file name, and it never affects type. It's a small bend of your "only the code matters" rule. Is that acceptable?

Yes its acceptable beacuse its necessary. I wanted to know how are we going to do this explain in siple step by step points

Here's the process, one pass per step.

Load. Read inventory.json from Increment 2 to get the list of files and their types.
Re-read each file with the reader, so we have the cleaned code lines with real line numbers (comments already removed).
Find the declared name, using the type to pick the rule:
program: the word after PROGRAM-ID.
JCL job: the name on the //NAME JOB card
JCL proc: the name on the //NAME PROC line
BMS: the name on the DFHMSD line (the mapset) and each DFHMDI line (the maps)
assembler: the label before CSECT
copybook: no declared name, so we use the file name without folder or extension
Find references, one small regex per kind, run over the cleaned lines:
COPY X, or EXEC SQL INCLUDE X
CALL 'X' (a name in quotes) is static; CALL VAR with no quotes is dynamic
EXEC CICS LINK / XCTL PROGRAM('X')
JCL EXEC PGM=X and EXEC procname
EXEC CICS SEND MAP('M') / RECEIVE MAP('M')
Each reference is saved as kind, name, and line number.
Build a name table: declared name → file. If two files declare the same name, record both in duplicates.
Resolve each reference by looking up its name in the table:
found → link it to that file
in a short built-in list of IBM-supplied names (SQLCA, SQLDA, IEFBR14, SORT, IDCAMS, DFHAID and similar) → mark system
a CALL with a variable → mark dynamic
anything else → add it to gaps
Find entry points:
every JCL job
programs with RECEIVE MAP or RETURN TRANSID (online, inferred)
programs no other file calls (root, inferred)
Add a hash (SHA-256) of each file's bytes.
Write the results back into inventory.json and show the gaps and entry points on the web page.
Everything is repeatable code with no LLM, so a wrong result always means a fixable rule.

Shall I write the Increment 3 prompt now?

## Progress report — Stage 1 inventory, progress, and sorted copies

**Implemented**
- Classifies files by content, with type, confidence, evidence, scores, and runner-up.
- Runs inventory in the background. The page polls for per-file progress, shows it in a collapsible log, and offers a **Stop** button. Stop takes effect between files; completed classifications are saved.
- Saves timestamped JSON inventories in workspace/stage1_outputs/, named <source-directory>_inventory_YYYYMMDD_HHMMSS.json.
- Copies each file into workspace/sorted_<source-directory>/<type>/<filename> as it is classified. Copies from completed files remain after stopping. Duplicate basenames in the same type folder overwrite.
- Submits **Run** without navigating to a new page or opening a tab; results load into the current page.

**Relevant files**
- app.py
- inventory.py
- index.html
- test_classifier.py

**Validation and known issue**
- The latest focused classifier and reader test run passed: **29 passed**.
- The same-page inventory flow was smoke-tested in the browser.
- The full suite has a pre-existing failure in test_scanner.py: its Windows path is passed as a regex to pytest.raises(match=...). The scanner and its tests were left unchanged.

**For the next increment:** Preserve the current progress/stop workflow and the JSON and sorted-folder output conventions unless the new requirements explicitly change them.

this si the progress report of laat increment. give the prompt for increment 3


Ran 2 commands
Ran 2 commands
Continue

Here's the Increment 3 prompt. I changed one thing from my earlier plan: names and references are extracted in the same per-file loop that already classifies each file, so nothing is read twice. The linking step then runs once after the loop. The prompt tells Copilot to read your existing code first, so the progress log, Stop button and sorted copies keep working as they do now.

You are a programmer who writes exactly what is specified below. Do not add features,
files, classes, config, logging, or libraries that are not listed. If something is
unclear, choose the simplest option and add nothing extra. Keep the code easy to read:
short functions, clear names, a one-line docstring on each function.

FIRST: read app.py, inventory.py, templates/index.html and the existing tests. Keep the
existing behavior exactly: background run, per-file progress log, Stop button, timestamped
JSON in workspace/stage1_outputs/, sorted copies in workspace/sorted_<source>/<type>/,
same-page result loading. Follow the existing style for progress messages and for
delivering results to the page.

GOAL
For every file, also record (a) the name the file declares for itself and (b) the things
it refers to (copybooks, called programs, JCL programs/procs, CICS maps). After all files
are processed, match references to declared names, and report gaps (references with no
matching file), entry points, and duplicates. Never use an LLM. Types are never decided by
file names. The only use of a file name is the stem rule below.

CHANGES
  NEW   stages/stage1_inventory/extractors.py
  NEW   stages/stage1_inventory/linker.py
  NEW   tests/test_extractors.py
  NEW   tests/test_linker.py
  EDIT  inventory.py       (call extractors per file, call linker at the end)
  EDIT  app.py / index.html (show new data)
  EDIT  tests/test_scanner.py  (small test fix, see the end)
Do not change classifier.py, scorers.py, reader.py, scanner.py.

extractors.py
  One public function:
    extract(content: FileContent, file_type: str, rel_path: str)
        -> tuple[list[str], list[dict]]
  Returns (declared_names, references). All names are uppercased and stripped.
  Each reference is {"kind": str, "name": str, "line": int, "dynamic": bool}.
  Use content.code_lines (comments already removed) unless stated. Case-insensitive regexes,
  compiled once as module constants.

  Declared names, chosen by file_type:
    cobol_program : every match of  ^\s*PROGRAM-ID\.?\s+['"]?([A-Z0-9][A-Z0-9-]*)
    jcl           : first match of  ^//([A-Z0-9#@$]+)\s+JOB\b
    jcl_proc      : first match of  ^//([A-Z0-9#@$]+)\s+PROC\b ; if none, the file stem
    bms_map       : USE content.raw_lines (not code_lines). Matches of
                    ^([A-Z0-9#@$]+)\s+DFHMSD\b  (mapset) then ^([A-Z0-9#@$]+)\s+DFHMDI\b (maps),
                    in that order
    assembler     : USE content.raw_lines. Matches of ^([A-Z0-9#@$]+)\s+(CSECT|RSECT|START)\b
    pli           : first match of ^\s*([A-Z0-9#@$_]+)\s*:\s*(PROC|PROCEDURE)\b
    copybook, cobol_fragment : the file stem
    any other type: []
  File stem = file name without folder and without extension (os.path.basename, then
  os.path.splitext), uppercased. This stem rule is the ONLY place a file name is used.

  References, only for these types: cobol_program, cobol_fragment, copybook (copybooks may
  contain COPY lines), jcl, jcl_proc, assembler is skipped. Kinds:
    copy        : lines matching  ^\s*COPY\s+["']?([A-Z0-9][A-Z0-9_-]*)
    sql_include : EXEC\s+SQL\s+INCLUDE\s+([A-Z0-9][A-Z0-9_-]*)  (inside an EXEC SQL block)
    call        : \bCALL\s+(?:(["'])([A-Z0-9#@$_-]+)\1|([A-Z][A-Z0-9-]*))
                  quoted name -> dynamic False; unquoted name -> dynamic True
    cics_link / cics_xctl / cics_map / cics_transid : see EXEC blocks below
    jcl_pgm     : ^//\S*\s+EXEC\s+PGM=([A-Z0-9#@$]+)
    jcl_proc    : ^//\S*\s+EXEC\s+(?:PROC=)?([A-Z0-9#@$]+) but only when the line does NOT match
                  the jcl_pgm regex
    jcl_include : ^//\S*\s+INCLUDE\s+MEMBER=([A-Z0-9#@$]+)
  "line" is the original line number of the line where the match starts.

  EXEC blocks: a helper exec_blocks(code_lines) returns (start_line, joined_text) for each
  EXEC CICS or EXEC SQL statement: start at a line containing EXEC\s+(CICS|SQL), join that
  line with the following lines (single spaces) up to and including the first line containing
  END-EXEC, at most 15 lines. Run the sql_include and CICS regexes on joined_text:
    cics_link   : EXEC CICS LINK ... PROGRAM(<x>)
    cics_xctl   : EXEC CICS XCTL ... PROGRAM(<x>)
                  <x> is a quoted literal -> dynamic False; unquoted -> dynamic True
    cics_map    : EXEC CICS SEND MAP or RECEIVE MAP (also SEND/RECEIVE with MAP anywhere).
                  Name = the value of MAPSET('..') if present, otherwise MAP('..'). Create one
                  reference per EXEC CICS statement.
    cics_transid: EXEC CICS RETURN ... TRANSID('..')  (only when TRANSID is present)
  Make sure a statement is not counted twice (the plain line regexes above must not run
  on CICS/SQL lines that were already handled by exec_blocks).

linker.py
  Constants:
    SYSTEM_NAMES = {"SQLCA","SQLDA","DFHAID","DFHBMSCA","DFHEIBLK","IEFBR14","IEBGENER",
                    "IEBCOPY","IEBCOMPR","IEBUPDTE","IDCAMS","SORT","ICEMAN","ICETOOL",
                    "IKJEFT01","IKJEFT1B","DSNTEP2","DSNTEP4","DSNUTILB","DSNTIAUL",
                    "IGYCRCTL","IEWL","IEWBLINK","ADRDSSU"}
    SYSTEM_PREFIXES = ("DFH","CEE","IEB","IEF","IEW","IGY","IKJ","DSN","ICE")
    ALLOWED_TYPES = which file types a reference kind may resolve to:
      copy, sql_include : copybook, cobol_fragment, sql
      call, cics_link, cics_xctl, jcl_pgm : cobol_program, assembler, pli
      jcl_proc, jcl_include : jcl_proc
      cics_map : bms_map
  One public function:
    link_inventory(files: list[dict]) -> dict
  Each element of files is a dict with at least: path, type, declared_names, references
  (list of dicts with kind, name, line, dynamic), sha256.
  Steps:
    1. Name table: uppercase name -> list of (type, path), from every file's declared_names.
    2. Resolve every reference IN PLACE by adding "status" (and "file" when resolved):
         - dynamic True                       -> status "dynamic"
         - kind cics_transid                  -> status "external"
         - name found in the table, filtered to the ALLOWED_TYPES of its kind
                                              -> status "resolved", file = first path sorted
         - else name in SYSTEM_NAMES or starts with a SYSTEM_PREFIXES item -> status "system"
         - else                               -> status "gap"
    3. gaps: group the "gap" references by name:
         {"name", "kinds": sorted unique kinds, "referenced_by": [{"file","line"}, ...]}
         sorted by name.
    4. entry_points: one entry per file, with the highest-priority kind that applies:
         "jcl_job"      : file type jcl                       -> inferred False
         "online"       : file type cobol_program with at least one cics_map or cics_transid
                          reference                            -> inferred True
         "root_program" : file type cobol_program, assembler or pli, NOT already listed, with
                          no inbound reference: no resolved reference from ANOTHER file with
                          kind call, cics_link, cics_xctl or jcl_pgm points to it
                                                               -> inferred True
       Each entry: {"name": first declared name or the path, "path", "kind", "inferred"}.
       Sorted by path.
    5. duplicates: {"names": [{"name", "files": [...]}] for names declared by 2 or more files
         of the same type,
       "identical_files": [[paths], ...] for groups of 2+ files with the same sha256}
    Return {"gaps": ..., "entry_points": ..., "duplicates": ...}.

inventory.py
  - In the existing per-file loop, after classify(): call extract(content, file_type, rel_path)
    and compute sha256 (hashlib) over the file's bytes (read in binary). Add to the file entry:
    sha256, declared_names, references (each with kind, name, line, dynamic).
  - After the loop finishes WITHOUT the user pressing Stop: write a progress line
    "Resolving references", call link_inventory(file_entries), and add the returned
    "gaps", "entry_points", "duplicates" at the top level of the inventory dict.
  - If the user pressed Stop: skip linking, set "gaps", "entry_points" and "duplicates"
    to empty lists/objects.
  - Add top-level "complete": true (finished) or false (stopped).
  - summary gets two more keys: "gap_count" and "entry_point_count".
  - Everything else (file naming, timestamps, sorted copies, progress, stop) stays unchanged.

index.html / app.py
  - Add a "Declared" column to the file table (declared names joined by ", ", "-" if none).
  - Below the file table add two sections, shown only when "complete" is true:
      "Gaps (N)"         table: Name | Kind | Referenced by (file:line, one per line)
      "Entry points (N)" table: Name | File | Kind | Inferred (yes/no)
  - Plain HTML. Same style as the existing tables.

tests/test_extractors.py  (pytest, tmp_path; write a file, read_file it, call extract with a
  file_type passed explicitly; lines of COBOL snippets start with 7 spaces)
  1. COBOL program: PROGRAM-ID. TESTPGM. COPY ACCTREC. COPY SQLCA. CALL 'SUBPGM'.
     CALL WS-PGM-NAME.  -> declared ["TESTPGM"]; references: copy ACCTREC, copy SQLCA,
     call SUBPGM (dynamic False), call WS-PGM-NAME (dynamic True), each with the right line.
  2. A line "           EXEC SQL INCLUDE SQLCA END-EXEC." gives sql_include SQLCA, and no copy.
  3. A comment line "      * COPY HIDDEN." (6 spaces, star in column 7) between other code lines
     gives no reference.
  4. CICS, multi-line:
           EXEC CICS XCTL
                PROGRAM('COMEN01C')
           END-EXEC.
           EXEC CICS SEND MAP('COSGN0A')
                MAPSET('COSGN00')
           END-EXEC.
           EXEC CICS RETURN TRANSID('CC00')
           END-EXEC.
     -> cics_xctl COMEN01C, cics_map COSGN00 (the mapset, not the map), cics_transid CC00.
     A "EXEC CICS LINK PROGRAM(WS-NEXT)" gives cics_link WS-NEXT with dynamic True.
  5. JCL (file_type "jcl"): lines
       //DAILY    JOB (ACCT),'X'
       //STEP1    EXEC PGM=TRANPROC,
       //         PARM='PROD'
       //STEP2    EXEC MYPROC,PARM=1
       //STEP3    EXEC PROC=OTHER
       //         INCLUDE MEMBER=INC1
     -> declared ["DAILY"]; jcl_pgm TRANPROC, jcl_proc MYPROC, jcl_proc OTHER, jcl_include INC1;
     no reference for the PARM line.
  6. BMS (file_type "bms_map") with the 4 lines of the earlier BMS test
     (MAPSET1 DFHMSD, MAP1 DFHMDI, FIELD1 DFHMDF, DFHMSD TYPE=FINAL) -> declared ["MAPSET1","MAP1"].
  7. Assembler (the earlier test G lines) -> declared ["MYPROG"].
  8. Copybook with rel_path "COPYLIB/acctrec.cpy" -> declared ["ACCTREC"]; rel_path "ACCTREC"
     (no extension) -> ["ACCTREC"]. jcl_proc with a "//MYPROC PROC" line -> ["MYPROC"];
     jcl_proc without a PROC line, rel_path "PROCS/PAYPROC.jcl" -> ["PAYPROC"].
  9. file_type "documentation" -> ([], []).

tests/test_linker.py  (build file dicts by hand)
  1. Program A (declared A) with refs: copy ACCTREC (no such file), copy SQLCA, call B (file B
     of type cobol_program declares B), call VAR with dynamic True, cics_transid CC00.
     -> statuses gap, system, resolved (file = B's path), dynamic, external.
     gaps contains exactly ACCTREC, with referenced_by [{file: A's path, line}].
  2. A call to "ACCTREC" when only a copybook named ACCTREC exists is a gap (kind/type filter).
  3. A copy of "ACCTREC" when a copybook file declares ACCTREC is resolved.
  4. A jcl_pgm reference to IEFBR14 is system. A name starting with "DFH" that has no file is system.
  5. Entry points: a jcl file -> jcl_job, inferred False. A program referenced by that JCL
     (resolved jcl_pgm) is NOT listed as root_program. An unreferenced program -> root_program,
     inferred True. A program with a cics_map reference -> online, inferred True (and listed once).
  6. A program that only calls itself is still a root_program (self references do not count).
  7. Two cobol_program files declaring the same name -> duplicates.names has it. Two files with the
     same sha256 -> duplicates.identical_files has a group with both paths.
  8. A jcl file and a cobol_program with the same declared name do NOT make a duplicate name.

tests/test_scanner.py (small fix)
  The test for the missing folder passes a Windows path to pytest.raises(match=...), which is
  treated as a regex and fails. Wrap the expected text with re.escape(...). Change nothing else.

DO NOT
  - read DB2 tables, files read/written, or paragraph structure (that is the next stage).
  - use an LLM, add libraries, abstract classes, or config files.
  - change the progress, stop, sorted-copy or JSON-naming behavior.
  - decide a file's type from its name; the stem rule above is the only use of a name.

HOW I WILL RUN IT (Windows PowerShell)
  python -m pytest
  python app.py
How to check the increment

All tests pass, including the repaired scanner test.
Run the banking repo. This is what I expect:
Gaps: ACCTREC, ERRHDLR, TRANREC and TRANPROC.
System: SQLCA, IEFBR14 and IEBGENER.
Resolved: RECONCIL and INTCALC (the JCL steps point to the two programs).
Entry points: the jobs DAILY and EOD, plus ACCTMSTR and UTILITY as inferred root programs, since nothing runs them.
Open the JSON: complete should be true, and a stopped run should show false with empty gaps.
I noticed one risk in your progress report. The sorted-folder copies overwrite files with the same basename in the same type folder. In a larger codebase, two different files named UTILS.cbl from different folders would lose one copy. The JSON still lists both, so it's only the copies that are affected, but it's worth fixing before you run CardDemo or CBSA.

How confident are we on our approach to find these names and references. What will it contribute in our next IR documnet json and what exactly is our approach to find thes enames an dreferences

I'm confident in the approach and less sure how well it works on real code. Everything so far has been tested only on synthetic snippets and your small banking repo, which has no CICS, BMS or nested copybooks.

How it finds names and references

The reader strips comments and the sequence-number columns, so a commented-out COPY or CALL is never counted.
Each file type has a fixed rule for its own name, such as PROGRAM-ID, the JCL job or proc name, or the mapset and map names. Copybooks have no name inside them, so they use the file name.
Short regex patterns find references: COPY X, CALL 'X', JCL EXEC PGM=X, and CICS LINK/XCTL/SEND MAP. CICS and SQL statements often span several lines, so these are joined first.
Each reference is matched against the table of declared names, and a reference may only match a file of a sensible type. For example, a CALL can't resolve to a copybook.
Anything unmatched is labelled system (IBM-supplied), dynamic (a variable), external (a transaction ID), or a gap.
How much I trust each part

High: PROGRAM-ID, JCL job and proc names, EXEC PGM=, plain COPY X and CALL 'X'. The syntax is standard.
Medium:
CICS statements, which I haven't run on any real file.
JCL procs invoked by name.
Matching copybooks by file name, which assumes the file name equals the copybook name. Real shops sometimes differ.
Weak spots:
CALL WS-PGM where a variable holds the program name. We can see it exists but not what it calls.
COPY ... REPLACING, and a COPY split across two lines.
JCL with symbolic parameters like &HLQ.
PL/I and assembler, where we find names but not their references.
Online entry points, because transaction-to-program links usually live in CICS definitions outside the code.
What it adds to the next IR
This is the skeleton the IR is built on:

Nodes: each file, its type and its declared names.
Edges: who calls, copies or runs whom, with line numbers.
Entry points and gaps, which the slicing stage depends on.
Increment 4 then adds the details inside each file: the DB2 tables, files read or written, and paragraph structure. The slicing stage needs both parts.

How we handle the uncertainty: nothing is silently guessed. Every unresolved or dynamic reference is listed with its file and line, so the failure cases are visible. Please run it on CardDemo or CBSA before we trust it, which will also test the CICS patterns.

Now lets discuss the next increment which is i think one of the most important increment. The prbfile ir...... D9nt henerate any prompt or anything just now..... First we will discuss the schema and all. So tell me what do you understand currently about per file IR and why do you think we are generating those and how would it contirbute in our final goal that is feature/module wise breaking of a big cobol codebase.

Stage 1 gives us a map of which files exist and who points at whom. The per-file IR records what is inside each file. The IR is the layer between raw code and both the LLM and the slicing logic.

Why we generate it: two consumers

The business-rules LLM step. Instead of sending a whole file, we send one paragraph at a time together with its structured context: what data it touches, what it calls, and what its inputs are. That keeps rules small, accurate, and traceable to line numbers.
The slicing step. This is the more important one. Feature boundaries in COBOL come from two things:
Control flow: who runs or calls whom. Stage 1 already has this at file level.
Shared data: which tables, files and records a program reads or writes. We don't have this yet. It's the main thing the IR adds.
What the IR would capture, by file type

COBOL program:
the paragraphs and sections with line ranges, and the PERFORM links between them
files declared (SELECT ... ASSIGN), with the ddname, and how they're used (read, write, update)
DB2 tables with the operation on each (select, insert, update, delete)
CICS maps, files and transaction IDs
parameters (LINKAGE), copybooks used, and size and branching counts
JCL: the steps in order, the program each runs, and every DD with its dataset and whether it's read, created or deleted.
Copybook: the record layout (fields, picture clauses, usage) and, for a DB2-generated one, the table it describes.
BMS: the screen fields.
The join that makes slicing work: a JCL DD name is the same name as the program's ASSIGN TO. That links a program's file to a dataset, and two jobs using the same dataset are data-coupled. The same goes for two programs touching the same table.

How it feeds the final goal
The graph gets two edge types: control (calls) and data (shared tables and datasets). A slice is everything reachable from an entry point. Slices that write the same data get merged. Data that is only read, or used almost everywhere, goes in the shared set, which becomes the interface when the pieces are rejoined. So read vs write is the single most important field.

Principles

No LLM. Tolerant line-based extraction that never rejects a whole file; anything it can't understand is recorded as "unparsed" with its line range.
Every fact carries its line numbers.
A field goes into the schema only if some later step needs it.
Honest limits: SQL built dynamically, file or table names held in variables, and PERFORM ... THRU ranges are hard. We'll flag these rather than guess.

Question: should the first version cover COBOL programs and JCL only, since they carry control and data coupling, and add copybook layouts and BMS later? I think so, to keep this increment testable.

Files hidden when shared
This are some of images that shows a ir json created by my colleges for a vb. Net codebase. Can something from this be relevant to our project. The fields and their itputs will give you an didea

Yes. The overall structure carries over well, but the contents are different, and a few things visible in the screenshots are lessons in what to avoid. This is from the screenshots only, since I haven't seen their code.

What I'd reuse

Two-level layout. Their Files list has one entry per file with RelativePath, Sha256, Lines and an IrFile pointer to a separate per-file JSON. The consolidated document stays an index, and the details live in per-file files. This matches your supervisor's flow and keeps each file small enough to send to an LLM.
Stable IDs like T:..., M:..., F:.... We need the same for COBOL, for example PGM:ACCTMSTR, PARA:ACCTMSTR.200-PROCESS, DS:USER.TRANOUT, TBL:ACCOUNT. Without them you can't build edges.
A source span on everything (start and end line, and column). We would use line ranges, which also give the LLM and reviewers a direct way back to the code.
Calls as edges with TargetId, Kind, IsResolved and the span. This is the same idea as our references with resolved or gap.
Conditions per method (the If text plus its span). This is very useful for business rules. In COBOL it would be the IF, EVALUATE and WHEN conditions per paragraph.
Hints and status fields: ClassificationHints, AnalysisStatus, Metrics, per-file Diagnostics, SchemaVersion, GeneratedAtUtc.
ConfigurationArtifacts (non-code files with a kind). For us that's JCL, BMS and DDL.
ExternalDependencies kept separate from UnresolvedSymbols. This is the same split as our system versus gap.
What doesn't transfer

Namespaces, classes, inheritance, generics and visibility have no COBOL equivalent. Our units are programs and paragraphs. In place of types and fields we have data items (level, picture, usage).
Their IR seems to have no data-access edges. We need them most: tables and files, each marked read or write.
Lessons from their weak spots

Almost everything is unresolved. ResolvedType is null and IsResolved is false nearly everywhere, and the diagnostics say things like "System.Void is not defined". Their compiler had no references to work with.
Noise drowns the signal. UnresolvedSymbols is mostly designer-generated calls like CType(...).BeginInit, which is why the list is huge. We should filter noise and only list real gaps.
RawCode and NormalizedCode repeat the source in many places, so the file balloons. We should store line ranges and read the text on demand.
They depend on a real compiler for resolution. We have no COBOL compiler, so our extraction stays tolerant and pattern-based.
Question: should our top-level shape deliberately match theirs (same key names where the idea is the same), so tools like slicing can work across both? It's cheap now and expensive later. Or should we design for COBOL first and align later?

Files hidden when shared
No no we dont have to copy anything from that ir if not necessary, it was just a relevant input to learn from if helpful. Hereare the remianig images


Updated memory
Updated memory
Understood, we'll design the COBOL IR on its own terms. These last images show a few ideas worth keeping in mind, though.

Useful ideas

One edge list for all relationships. Each edge has From, To, Kind, SourceFile, Line and IsResolved. Our version would carry control edges (calls, runs, copies) and data edges (reads, writes) in the same list, which makes slicing a graph problem.
Strongly connected components (the field is empty in theirs). For us it matters directly: programs that call each other in a cycle can't be split, so each cycle is one unit in a slice.
Honest quality flags. AnalysisStatus marks each part as Complete or Partial and sets Authoritative: false. We should say plainly which parts of our IR are partial, such as unresolved references or unparsed line ranges.
A health ratio. Their metrics show about 135 internal edges against roughly 7,300 unresolved. That ratio tells you at a glance that the IR is not trustworthy. We'd report resolved versus unresolved edges the same way and treat a bad ratio as a warning before any LLM step runs.
Metrics block with counts such as conditions and stored-procedure calls. The equivalents for us would be paragraphs, SQL statements, conditions and files per program.
What I'd skip

The suggested migration order. It's for conversion, which your supervisor said to leave out. We'd still keep the cycles, since slicing needs them.
The large unresolved-symbol and diagnostic lists. They're mostly noise from a missing compiler.
Next step: I'd draft the schema now for COBOL programs and JCL only, since they carry the control and data links that slicing needs. Copybook layouts and BMS screens would come after. Is that scope OK?

No no remeber we have to deduce a conversion order. Thats the main thing my supervisor wants in ir. By his logic an ir is a systematic and structured representation of the codebase so he  assumes that the ir knows in very detail how componenets are weaved together and hence coupd be used as a knowledge base to to find out a conversion order of files in least dependent to mlst depnedent order.

You're right, I misread that. Your supervisor doesn't want conversion done, but he does want the IR to be rich enough to deduce a conversion order. So the order is a required output, and the IR should be designed around it.

How the order would be computed (deterministic, no LLM)

Build one directed graph where an arrow means "needs": A → B means B must exist before A can be converted.
Group cycles. Programs that call each other in a loop can't be ordered against each other, so each cycle becomes one unit.
Do a topological sort of the result. Leaves (things that need nothing) come first, and the most dependent come last. Items at the same depth form a "wave" that could be converted in parallel.
Break ties inside a wave by a simple rule, such as fewest dependents first or smallest first.
Edges that count for ordering

Hard (must come first): COPY (the copybook first), CALL/LINK/XCTL (the callee first), and a JCL step running a program (the program first, so JCL is naturally near the end).
Data (my proposal): a program that reads or writes a table or dataset depends on that data being defined, so the data model comes before its users. This is what puts "database models" at the start of a Flask rewrite.
What this requires from the IR

Every edge is typed, directional, has a line number, and carries a status (resolved, system, dynamic or gap).
Nodes for programs, copybooks, JCL jobs, screens and data stores, each with a stable ID.
Order computed at file and program level. A program is converted whole, so paragraph detail stays for the business rules and isn't needed for order.
A confidence flag on the order. A gap (missing source) is treated as a leaf but flagged, and a dynamic CALL means the order may be incomplete. The output should say so.
How it ties to slicing: order the whole codebase first, then each slice inherits its order. Anything shared goes first because everything depends on it, and the slices can then be converted one at a time.

Question: do you want data stores (tables and datasets) to appear in the order as their own items, placed before the programs that use them? I'd say yes, since the model definitions have to exist first.

Okay lets now discuss the json schema for ir. Propose to me a schema with every field defined and what it would capture

Here's the proposed schema. It has two layers: one small IR file per source file, and one consolidated project_ir.json that joins them into a graph with the conversion order. Every fact carries a line number. Raw source text is never copied in, except short normalized condition text.

A. Consolidated project_ir.json
schema_version, generated_at, source_folder: bookkeeping.
files[] (index only):
path, type, sha256, lines.
ir_file: pointer to the per-file IR.
declared_names: names the file declares.
parse_status: complete or partial.
nodes[]: everything that can be depended on.
id: pgm:ACCTMSTR, cpy:ACCTREC, job:DAILY, proc:X, map:COSGN00, tbl:ACCOUNT, ds:USER.TRANOUT.
kind: program, copybook, jcl_job, jcl_proc, bms_map, table, dataset.
name.
defined_in: file path, or null.
status: defined, system (IBM-supplied), gap (no source found) or dynamic.
edges[]: every relationship.
from, to: node IDs.
kind: copies, calls, links, xctl, runs_program, runs_proc, includes, uses_map, reads, writes.
file, line: where the edge was found.
status: resolved, system, gap or dynamic.
access: for data edges: read, write, read_write or unknown.
inferred: true if derived (for example from JCL DISP).
entry_points[]: node, kind (jcl_job, online, root_program), inferred.
cycles[]: id, members[]. Mutually dependent groups that can't be split.
conversion_order:
basis: the edge kinds used.
waves[]: each with wave (number) and units[].
Each unit has id, members[] (a node or a cycle), depends_on[] (units) and notes (for example "depends on a gap").
quality:
Counts per node status and edge status.
resolved_ratio.
unparsed_files[].
order_complete (bool) and caveats[].
B. Per-file IR, common header
path, type, sha256, lines, encoding, source_format, declared_names[], parse_status, and unparsed_ranges[] with start, end, reason. If a part can't be understood, it is recorded here, and the file is never rejected.

C. Per-file IR, COBOL program (program)
id, name, line_span.
dialect: cbl_cards[] (compiler directive lines), uses_sql, uses_cics, copy_replacing (bool).
files[]: one per file the program uses.
logical_name (the SELECT name), ddname (the ASSIGN TO name).
organization, access_mode, status_var.
open_modes[]: input, output, i-o, extend.
operations[]: READ, WRITE, REWRITE, DELETE.
access: derived read, write or read_write.
lines[].
copybooks[]: name, line, section (where it's copied), replacing (bool).
data_items[]: name, level, pic, usage, section, redefines, occurs, value, line. This is a flat list for later business-rule context.
linkage: is_subprogram (has PROCEDURE DIVISION USING) and params[].
sql[]: one per EXEC SQL statement.
id, kind (select, insert, update, delete, declare cursor, open, fetch, close, include, other).
tables[], access (read or write), cursor, host_vars[].
dynamic (table name not visible).
paragraph, line_span.
cics[]: one per EXEC CICS command.
command, map, mapset, program, transid, file, queue, dynamic, paragraph, line.
calls[]: target, dynamic, args[], paragraph, line.
paragraphs[]:
name, line_start, line_end.
performs[]: target, thru, line.
goto[]: targets.
sql_refs[], cics_refs[], call_refs[]: IDs of the items above used here.
file_ops[]: op, file, line.
conditions[]: kind (IF, EVALUATE, WHEN), text (normalized, at most 120 characters), line.
ends (STOP RUN, GOBACK or EXIT).
metrics: counts of paragraphs, conditions, sql, cics, calls and lines.
D. Per-file IR, JCL (jcl)
kind: job or proc.
name, line_span.
steps[]:
name, order, line_span.
exec_kind (pgm or proc), target, parm, cond.
dds[]: ddname, dsn, disp, kind (input, output, new, delete, sysout, dummy, inline, concat), access, inferred.
includes[]: member, line.
E. Copybook and BMS (light, so they exist as nodes)
Copybook: copies[] (nested), data_items[] as above, and declares_table (for DB2-generated ones).
BMS: mapset, maps[], and fields[] with name, length and line.
The key join, done at consolidation time: a program's ddname is matched to the DD in the JCL step that runs it, which creates the ds: node and the reads/writes edge. That is how two jobs or programs become connected through shared data.

How the order uses this: copies, calls, links, xctl, runs_program, runs_proc, includes and uses_map make the dependent need the target first. Data edges make a program need its table or dataset defined first. Cycles are merged into one unit, and the rest is sorted into waves.

Question: is paragraph-level detail enough (which paragraph does what to which file, table or condition), or do you also want tracking of which data items each paragraph reads and writes? The second is much heavier, and I'd leave it out unless your supervisor wants it.

Files hidden when shared
If created atleast 60 percent....... It could be used to generate documnets like project understanding document, technical specification document, dataflow diagram (visual diagrams using mermaid in pdf) activityflow digrams (visual diagrams using mermaid in pdf) etc. right
Becuase using the json i gave you in images i wrote scripts that would make these diagram. Refer to attached scripts


Ran 2 commands
Ran 2 commands
Yes, with one condition. Documents like these can be generated from the IR, but how much depends on which parts of the IR are filled in well, not on a percentage of the schema. I read your scripts to check.

Which documents depend on which part of the IR

Document	What it needs from our IR
Dependency graph, impact analysis, cycles, conversion order	Only nodes and edges. Your generate_dependency_graph.py does levels, cycle collapsing and impact analysis on generic edges, so that logic carries over almost unchanged.
Architecture graph	Node kinds. For COBOL the "layers" would be online (CICS), batch (JCL), shared utility and data. The layer rules need rewriting.
Data flow diagram and CRUD matrix	The reads/writes edges and the JCL DD links. This is new for COBOL but easy once the edges exist.
Activity flow (per-program flowchart)	Paragraphs with performs, goto and conditions. Your TSD already draws flowcharts for the most complex methods, and this is the same idea.
Job flow	JCL steps in order.
PUD and TSD (narrative)	The LLM pipeline you built: facts extracted deterministically, a small LLM call per unit, then one call per section. Only the IR readers and prompts change, from types and forms to programs and paragraphs.
Your scripts' cached calls, confidence banner and the rule that Python builds tables and diagrams while the LLM writes only narrative are all worth keeping. The graph and diagram documents are the ones to trust early, because they need only the structural parts.

Two gaps I see in our schema

Source text. Your IR carries RawCode and NormalizedCode, and the LLM digests use them. Ours stores only line spans. That's fine if the generators read the lines from the codebase folder (your IR_BASE_DIR idea), with the hash to detect changed files. If the IR must stand alone as the knowledge base, we'd have to embed snippets.
Two facts your TSD uses that we don't capture yet. One is error handling: your scripts count Try/Catch, and the COBOL equivalent is SQLCODE and FILE STATUS checks, INVALID KEY, ON SIZE ERROR and RETURN-CODE. The other is user-facing messages: DISPLAY literals and screen messages. I'd add error_checks[] and messages[] per paragraph.
One more note: the diagrams are only as truthful as the resolved ratio. Your banner on unresolved edges is the right habit, and I'd keep it. Also, turning Mermaid into PDF is a separate rendering step, and your scripts currently produce Markdown and HTML.

I'd also reuse your edge field names (From, To, Kind, SourceFile, Line, IsResolved) in our edges, so your dependency and architecture scripts need only small changes. That's a cheap, practical reason to align.

Question: should the IR be self-contained (short normalized snippets embedded, bigger files), or line spans only with the source read on demand? I'd choose line spans plus the file hash.

Teh ultimate goal is we must be able to identify at which point activity is starting and whats happening, like it should help us get familiar with the project. Hence we have to design ir according to that.


Updated memory
Updated memory
That changes the schema's center of gravity. My draft was organized as a dependency graph. If the goal is "where does an activity start, and what happens next?", the IR needs to be organized around flows. The graph stays as the base layer, and a flow layer sits on top of it.

Changes to the schema

entry_points[] becomes the main object. Each one carries:
trigger: what starts it, such as a batch job, a user transaction (with its transaction ID and map), or "called by nobody", with a confidence flag.
trace: the ordered list of what happens, described below.
touches: the data stores read and written, the screens shown, and the external programs called.
reach: the programs and copybooks involved.
summary: left empty by the deterministic stage and filled later by the LLM.
Paragraphs get one ordered events[] list, in source order. In my draft they had separate lists (sql, file ops, calls), which loses the order. An event is one of: perform, file_op, sql, cics, call, display, error_check, end. Each has a line number and under (the id of the condition it sits inside, so we know "only if the balance is low").
Conditions are first-class with an id and normalized text, so a trace can say "if X, then these events".
JCL steps stay ordered, so a job reads as a sequence.
The trace is built by walking: job steps → the program each runs → its paragraphs from the first one, expanding PERFORMs in order (with a depth limit and a loop guard), and for online programs following XCTL and RETURN TRANSID to the next program.
A project overview block for orientation: entry points sorted by size, the most-shared items, and for each data store who reads and who writes it.
Example, from your banking repo's DAILY job (JCL only, programs not yet expanded)

START  batch job DAILY (JCL)
 1 PREPARE  runs IEFBR14 (system)   deletes four output datasets
 2 MAIN     runs TRANPROC (GAP: source missing)  reads TRANSACTIONS, writes TRANOUT and ERRLOG
 3 EODPROC  runs RECONCIL           reads TRANOUT, writes RECONCIL report
 4 REPORT   runs IEBGENER (system)  prints TRANOUT
Expanding step 3 would open RECONCIL and show its paragraphs in order, with the SQL and file operations inside each.

What stays out of the deterministic stage: the plain-English meaning of each step. The IR holds the skeleton and where each part lives in the code, and the LLM step later writes the summary fields from it.

Question: for the trace, is two levels right? Level 1 (always built): the entry point, its steps or programs, and the data touched. Level 2 (per program, built on demand): the paragraph-by-paragraph flow. I'd choose this so the first view stays readable.

No no all these are important goals, the documents built from ir would help us understand project but the ir should also contirbute importantly into breaking and bundling of big codebase into multiple small codebases module wise.

Understood. The IR has to do three jobs at once: help people understand the project, deduce a conversion order, and support splitting it into modules. I'll design it in layers, so each job gets what it needs and each layer can be tested on its own.

The four layers

Facts (per file): names, paragraphs and their ordered events, SQL and file operations, JCL steps, calls, copies, with line numbers.
Graph: nodes (programs, copybooks, jobs, screens, tables, datasets) and typed edges. This layer also holds the cycles and the conversion order.
Flows: entry points and the trace of what happens from each one. This is for understanding.
Modules: the breakdown into small codebases. This is new in the design.
What the module layer needs that the earlier schema didn't have

On every node: used_by (which entry points reach it) and fan-in and fan-out. A node used by many entry points is a candidate for the shared set.
On every data store: readers[] and writers[]. Shared data is the strongest sign that two entry points are one feature.
On every entry point:
reach: everything it needs to run, found by following copies, calls, links, XCTL, runs and includes. This is what makes a slice standalone.
touches: the data stores it reads and writes. Stores are interfaces, not code to copy.
coupling[]: for each pair of entry points, how many code nodes they share, how many data stores they read in common, and how many they write in common.
modules[] (filled in by the slicing stage, but defined in the schema so the output has a home):
id, name, entry_points[], members[] (nodes).
shared_dependencies[]: shared nodes the module relies on.
interfaces[]: data stores with read or write mode, and calls into other modules.
gaps[]: missing source the module depends on.
internal_order: the conversion waves inside the module.
shared[]: nodes used by two or more modules, with the reason.
boundary_edges[]: every edge that crosses a module boundary. After the pieces are converted, these edges are exactly what has to be reconnected.
module_order: the conversion order between modules, since modules form a graph too.
How one IR serves all three

Goal	Uses
Understanding	flows, events, summaries
Conversion order	edges, cycles, waves
Breakdown	reach, coupling, modules, shared set, boundary edges
How a slice is built (deterministic):

Start from an entry point and take its reach.
Merge entry points that write the same data store.
Put nodes used by several modules in the shared set.
Record what crosses the boundary.
The LLM only names each module and flags suspicious groupings.
Question: when two entry points write the same table, my default is to merge them into one module. The alternative is to keep them separate and mark that table as a shared interface between two modules, which gives smaller modules but riskier reintegration. Do you want the merge default?

Okay it think i have gave you my requirements well enough.... Anything not accoriding to our needs would be informed later so we will ywitchin the json ir. For now give me the final ir schema that you would explain in prompt for copilot

This is the final schema, written so you can paste it into Copilot prompts. I fixed three open points with my defaults. They're listed after the schema, so change them if you disagree.

IR SCHEMA v1.0

CONVENTIONS
- Keys are snake_case. Names are uppercase. Lines are 1-based original line numbers.
- Every fact carries file + line (or line_span [start, end]).
- Source text is never stored, except normalized condition text (max 120 chars)
  and DISPLAY literals (max 80 chars).
- Unknown = null. Empty list = []. Never guess a value.
- status (nodes and edges): "resolved" | "system" | "gap" | "dynamic" | "external"
- Node ids: pgm:X  cpy:X  job:X  proc:X  map:MAPSET  tbl:X  ds:DSN  dd:DDNAME
  (dd: only when a program's DD name has no matching JCL)
- Derived ids: para:PGM.PARA  sql:PGM.n  cics:PGM.n  call:PGM.n  cond:PGM.n
  ep:<node id>  cyc:n  u:n  mod:NNN

=== A. PER-FILE IR  (ir/<relative path>.ir.json) ===
HEADER (all files)
  schema_version, path, type, sha256, lines, encoding, source_format,
  declared_names[], parse_status: "complete"|"partial",
  unparsed_ranges: [{start, end, reason}]
  plus exactly one of: program | jcl | copybook | bms

program: {
  id, name, line_span,
  dialect: {cbl_cards[], uses_sql, uses_cics, copy_replacing},
  files[]: {logical_name, ddname, organization, access_mode, status_var,
            open_modes[] (INPUT|OUTPUT|I-O|EXTEND),
            operations[] (READ|WRITE|REWRITE|DELETE|START),
            access: "read"|"write"|"read_write"|"unknown", lines[]},
  copybooks[]: {name, line, replacing},
  data_items[]: {name, level, pic, usage, redefines, occurs, value, line},
  linkage: {is_subprogram, params[]},
  sql[]: {id, kind (select|insert|update|delete|declare_cursor|open|fetch|close|
          include|commit|rollback|other), tables[], access ("read"|"write"|null),
          cursor, host_vars[], dynamic, paragraph, line_span},
  cics[]: {id, command, map, mapset, program, transid, file, queue, dynamic,
           paragraph, line},
  calls[]: {id, target, dynamic, args[], paragraph, line},
  conditions[]: {id, kind (IF|EVALUATE|WHEN|UNTIL), text, paragraph,
                 parent (cond id|null), line_span},
  paragraphs[]: {id, name, line_start, line_end, events[]},
  metrics: {paragraphs, conditions, sql, cics, calls, lines}
}

event (in source order inside a paragraph):
  {seq, kind, line, under (cond id|null), ...}
  kind perform     : target, thru, loop (true if UNTIL/VARYING/TIMES)
  kind goto        : target
  kind file_op     : op (OPEN|CLOSE|READ|WRITE|REWRITE|DELETE|START), file, mode
  kind sql         : ref (sql id)
  kind cics        : ref (cics id)
  kind call        : ref (call id)
  kind display     : text
  kind error_check : what (SQLCODE|FILE_STATUS|INVALID_KEY|AT_END|ON_SIZE_ERROR|
                     ON_EXCEPTION|RETURN_CODE), var
  kind end         : how (STOP_RUN|GOBACK|EXIT_PROGRAM|CICS_RETURN|ABEND)

jcl: {
  kind: "job"|"proc", id, name, line_span,
  steps[]: {name, order, line_span, exec_kind: "pgm"|"proc", target, parm, cond,
            dds[]: {ddname, dsn, disp, kind (input|output|new|delete|sysout|dummy|
                    inline|concat|other), access ("read"|"write"|"read_write"|"unknown"|null),
                    inferred (true: guessed from DISP), line}},
  includes[]: {member, line}
}
  DD access from DISP only: NEW/MOD -> write, SHR -> read, SYSOUT -> write,
  DUMMY -> null. Always inferred = true. Program file access overrides it (see B).

copybook: {id, name (file stem), copies[]: {name, line}, data_items[],
           declares_table (name|null)}
bms:      {id (map:MAPSET), mapset, maps[]: {name, size, line}, field_count}

=== B. CONSOLIDATED  project_ir.json ===
{ schema_version, generated_at, source_folder, complete (false if run was stopped),

  files[]: {path, type, sha256, lines, ir_file, declared_names[], parse_status},

  nodes[]: {id, kind (program|copybook|jcl_job|jcl_proc|bms_map|table|dataset),
            name, defined_in (path|null), status,
            used_by[] (entry point ids that reach it), fan_in, fan_out,
            readers[], writers[]  (node ids; only for table/dataset)},

  edges[]: {from, to, kind, source_file, line, status, access, inferred}
     kind: copies | calls | links | xctl | runs_program | runs_proc | includes |
           uses_map | reads | writes
     access: "read"|"write"|"read_write"|"unknown" for reads/writes, else null
     A program that both reads and writes a store gets two edges.
     Data joins: a program's file ddname = the DD name in the JCL step that runs it
       -> edge program -> ds:DSN. The program's own access wins over the DD guess.
     Steps running a utility or a program with no IR: edge job -> ds, inferred = true.

  entry_points[]: {id, node, kind (jcl_job|online|root_program), inferred,
       confidence ("high" all reach resolved/system | "medium" any dynamic | "low" any gap),
       trigger: {type (batch|user|none), name (job name|transid|null), source_file, line},
       steps[]: {order, name, node, status, reads[], writes[], maps[], next[]},
         job: its steps in order. online: the program, then XCTL/LINK targets in
         line order (depth limit 10, loop guard). root_program: itself, then the
         programs it calls in order of first call line.
       reach[]: node ids reachable via copies, calls, links, xctl, runs_program,
                runs_proc, includes, uses_map (no data edges),
       touches: {reads[], writes[], screens[], external[] (system/gap nodes)},
       summary: null }       // filled later by the LLM stage

  cycles[]: {id, members[] (node ids), via[] (edge kinds)}

  conversion_order: {
     basis: ["copies","calls","links","xctl","runs_program","runs_proc","includes",
             "uses_map","reads","writes"],     // from depends on to
     waves[]: {wave, units[]: {id, kind ("single"|"cycle"), members[], depends_on[]
                               (unit ids), notes[]}},
     excluded[]: {node, status},               // system / gap / dynamic: not convertible
     complete, caveats[] }
     Rules: a cycle collapses to one unit. wave 0 = no dependency on a defined unit,
     else 1 + max wave of its dependencies. Data stores are units and come before the
     programs that use them. Units in a wave are sorted by id.

  coupling[]: {a, b (entry point ids), shared_code[], shared_reads[], shared_writes[],
               a_to_b[] (stores a writes and b reads), b_to_a[]}
     Only pairs with at least one non-empty list. shared_writes non-empty = merge candidate.

  // Filled by the slicing stage; empty lists until then
  modules[]: {id, name, entry_points[], members[], shared_dependencies[],
              interfaces: {stores[]: {node, access}, calls_out[]}, gaps[],
              internal_order[] (waves)}
  shared[]: {node, used_by_modules[], reason}
  boundary_edges[]: {from, to, kind, from_module, to_module}
  module_order[]: waves of modules, same shape as conversion_order.waves

  quality: {counts: {files, by_type{}, nodes_by_status{}, edges_by_status{}},
            resolved_ratio (edges resolved+system / all edges),
            unparsed_files[], authoritative (false if any gap, dynamic or unparsed),
            caveats[]} }
Defaults I fixed

Line spans plus hash: no source text is stored. Generators read lines from the codebase.
Merge rule: entry points that write the same data store are merged into one module. Stores that are only read go to the shared set.
Two-level flow: the entry-point steps[] are stored. The paragraph-by-paragraph flow is derived from paragraphs[].events when needed, not stored.
Build order (each increment is testable)

4a: per-file IR for COBOL programs and JCL.
4b: copybooks and BMS.
5: nodes, edges and quality.
6: entry points, cycles and conversion order.
7: coupling and modules.
Shall I write the Copilot prompt for Increment 4a?

No no geretae the prompt for increment 4 of our original plan. Dont crete new increments.

Here's the Increment 4 prompt from the original plan: per-file IR for COBOL programs, copybooks, JCL and BMS, in one go. It writes one IR file per source file with no consolidation yet, which is Increment 5. The prompt follows the final schema, with one small addition: sql[].include holds the name for EXEC SQL INCLUDE.

You are a programmer who writes exactly what is specified below. Do not add features,
files, classes, config, logging, or libraries that are not listed. If something is
unclear, choose the simplest option and add nothing extra. Keep the code easy to read:
short functions, clear names, a one-line docstring on each function. Never use an LLM.

FIRST: read app.py, inventory.py, templates/index.html, reader.py, extractors.py and the
existing tests. Keep all Stage 1 behavior unchanged. Reuse the existing patterns for
background runs, per-file progress messages, the Stop button and same-page result loading.
Check the real function names (read_file, build_inventory, extract) before using them.

GOAL
For every file in the latest completed inventory, build a per-file IR JSON following the
schema below, and show a summary table on the page. Files are never rejected: anything
that cannot be understood is recorded in unparsed_ranges and parse_status "partial".

NEW / CHANGED FILES
  NEW  stages/stage2_ir/__init__.py
  NEW  stages/stage2_ir/common.py        (shared helpers)
  NEW  stages/stage2_ir/cobol_ir.py      (build_program_ir, parse_data_items)
  NEW  stages/stage2_ir/jcl_ir.py        (build_jcl_ir)
  NEW  stages/stage2_ir/copybook_ir.py   (build_copybook_ir)
  NEW  stages/stage2_ir/bms_ir.py        (build_bms_ir)
  NEW  stages/stage2_ir/builder.py       (build_file_ir: header + dispatch)
  NEW  stages/stage2_ir/runner.py        (run_ir: loops over the inventory, writes output)
  NEW  tests/test_ir_cobol.py, tests/test_ir_jcl.py, tests/test_ir_copy_bms.py,
       tests/test_ir_run.py
  EDIT app.py, templates/index.html      (Build IR button, progress, Stop, result table)
Do not change Stage 1 modules or tests.

CONVENTIONS (apply everywhere)
- Keys are snake_case and appear in the order written below. Names are uppercased.
- Lines are the original 1-based line numbers. Use content.code_lines (comments removed)
  unless a rule says raw_lines.
- Unknown = null, empty = []. Never guess. Never store source text, except normalized
  condition text (max 120 chars) and DISPLAY text (max 80 chars).
- Wrap each file's extraction in try/except. On an exception write the header with
  parse_status "partial" and unparsed_ranges [{start:1, end:lines, reason:"extractor error: <msg>"}]
  and continue with the next file.

builder.py
  build_file_ir(content, file_type, rel_path, declared_names, sha256) -> dict
  Header keys: schema_version "1.0", path, type, sha256, lines (len(raw_lines)), encoding,
  source_format, declared_names, parse_status ("complete"|"partial"), unparsed_ranges
  ([{start,end,reason}]). Then ONE body key by type:
    cobol_program -> "program" ; jcl or jcl_proc -> "jcl" ; copybook -> "copybook" ;
    bms_map -> "bms". Any other type: header only (no body key).
  declared_names comes from the inventory entry (computed in Stage 1).

common.py
  - statement_text(code_lines, i, max_lines=6) -> (text, end_line): join the line at index i
    with the following lines (single spaces) until the joined text ends with "." or the next
    line starts with one of these words (case-insensitive): MOVE PERFORM IF ELSE EVALUATE WHEN
    COMPUTE ADD SUBTRACT MULTIPLY DIVIDE DISPLAY ACCEPT READ WRITE REWRITE OPEN CLOSE CALL GO
    STOP GOBACK INITIALIZE STRING UNSTRING INSPECT SET EXEC END-<word> CONTINUE EXIT SORT MERGE
    RETURN RELEASE DELETE START CANCEL COPY SELECT FD, or a level number (01-49, 66, 77, 88).
  - find_exec_blocks(code_lines) -> list of {kind "SQL"|"CICS", start, end, text, closed}:
    a block starts at a line containing  \bEXEC\s+(SQL|CICS)\b , includes following lines up to
    and including the first line containing END-EXEC (max 15 lines). text = the joined lines,
    uppercased, spaces collapsed, without the leading "EXEC SQL|CICS" and without END-EXEC and
    a trailing ".". closed = False if END-EXEC was not found (then end = start + 14, capped).
  - normalize(text): strip, collapse whitespace.
  - paragraph_of(paragraphs, line) -> name or null.

cobol_ir.py  ->  build_program_ir(content, rel_path, declared_names) -> (program_dict, unparsed_ranges)
  Case-insensitive. Steps, in order:

  1. Divisions: find the first line matching each of ^\s*(IDENTIFICATION|ID)\s+DIVISION,
     ^\s*ENVIRONMENT\s+DIVISION, ^\s*DATA\s+DIVISION, ^\s*PROCEDURE\s+DIVISION. A line belongs
     to the division whose header precedes it. If there is no PROGRAM-ID or no PROCEDURE
     DIVISION, the result is partial (add an unparsed range covering all code lines, reason
     "no PROGRAM-ID" / "no PROCEDURE DIVISION"), and paragraphs = [].
  2. id "pgm:<NAME>", name from ^\s*PROGRAM-ID\.?\s+['"]?([A-Z0-9][A-Z0-9-]*), line_span
     [first, last] code line.
  3. dialect: cbl_cards = text after CBL/PROCESS at the start of any of the first 20 RAW lines
     (regex ^\s*(CBL|PROCESS)\s+(.*)$). uses_sql / uses_cics = any EXEC SQL / EXEC CICS block.
     copy_replacing = any COPY statement (this line plus the next 2 lines) containing REPLACING.
  4. files[] (FILE-CONTROL): each SELECT statement = statement_text from a line matching
     ^\s*SELECT\s+(?:OPTIONAL\s+)?([A-Z0-9-]+). Fields:
       logical_name = that name
       ddname: token after ASSIGN [TO] (strip quotes); remove ONE leading prefix from this list,
         tried in order: UT-S- DA-S- AS-S- UT- DA- AS- S-  (case-insensitive)
       organization: ORGANIZATION\s+(?:IS\s+)?(LINE\s+SEQUENTIAL|SEQUENTIAL|INDEXED|RELATIVE) or null
       access_mode: ACCESS\s+(?:MODE\s+)?(?:IS\s+)?(SEQUENTIAL|RANDOM|DYNAMIC) or null
       status_var: FILE\s+STATUS\s+(?:IS\s+)?([A-Z0-9-]+) or null
       open_modes, operations, access, lines: filled after step 8 (see there).
  5. FD records: in the FILE SECTION (from "FILE SECTION" to the next *-STORAGE/LINKAGE SECTION),
     ^\s*(FD|SD)\s+([A-Z0-9-]+) sets the current file; each ^\s*01\s+([A-Z0-9-]+) after it maps
     that record name to the current file. Used by WRITE/REWRITE.
  6. copybooks[]: every line matching ^\s*COPY\s+["']?([A-Z0-9][A-Z0-9_-]*): {name, line,
     replacing}. (EXEC SQL INCLUDE goes into sql[], not here.)
  7. data_items[] = parse_data_items(code_lines in the DATA DIVISION)  (function below).
     linkage: is_subprogram = the PROCEDURE DIVISION statement (joined to its ".") contains USING;
     params = the names after USING (drop BY, REFERENCE, CONTENT, VALUE, RETURNING and their
     following words, commas and periods).
  8. SQL and CICS blocks. Number blocks of each kind in order of start line: sql:<NAME>.n,
     cics:<NAME>.n (n from 1).
     sql[] item: {id, kind, tables, access, cursor, host_vars, include, dynamic, paragraph,
     line_span}. Use the block text:
       kind by first word(s): SELECT -> select; INSERT -> insert; UPDATE -> update; DELETE ->
       delete; DECLARE ... CURSOR -> declare_cursor; OPEN -> open; FETCH -> fetch; CLOSE -> close;
       INCLUDE -> include; COMMIT -> commit; ROLLBACK -> rollback; else other.
       tables: insert INTO\s+([A-Z0-9_.$#@]+); update UPDATE\s+([A-Z0-9_.$#@]+); delete
         DELETE\s+FROM\s+([A-Z0-9_.$#@]+); select/declare_cursor: take the FROM clause
         \bFROM\s+(.*?)(?=\bWHERE\b|\bGROUP\b|\bORDER\b|\bHAVING\b|\bUNION\b|\bFETCH\b|\bFOR\b|\bWITH\b|$),
         split it on commas, take the first token of each part (skip parts starting with "(" or ":"),
         and add every  JOIN\s+([A-Z0-9_.$#@]+)  name. Unique, in order.
       cursor: declare -> DECLARE\s+([A-Z0-9-]+)\s+CURSOR; open/close -> (?:OPEN|CLOSE)\s+([A-Z0-9-]+);
         fetch -> first token after FETCH that is not NEXT/PRIOR/FIRST/LAST/FROM.
         For open/fetch/close copy tables from the declare_cursor with the same name.
       access: select, declare_cursor -> "read"; insert/update/delete -> "write"; open/fetch/close ->
         the matching declare's access; otherwise null.
       host_vars: unique matches of :([A-Z][A-Z0-9-]*) in order.
       include: for kind include, the name after INCLUDE, else null.
       dynamic: true if the first word is PREPARE or EXECUTE (then kind "other", tables []).
       paragraph = paragraph_of(start line); null outside the PROCEDURE DIVISION.
     cics[] item: {id, command, map, mapset, program, transid, file, queue, dynamic, paragraph, line}.
       command = the first two words if they are in {SEND MAP, SEND TEXT, SEND CONTROL, RECEIVE MAP,
       READQ TD, READQ TS, WRITEQ TD, WRITEQ TS, DELETEQ TD, DELETEQ TS, HANDLE CONDITION,
       HANDLE ABEND, HANDLE AID, IGNORE CONDITION}, else the first word.
       map, mapset, program, transid, file (FILE( or DATASET( ), queue (QUEUE( or QNAME( ):
       regex (?<![A-Z-])KEY\(\s*(['"])?([A-Z0-9#@$_-]+)\1?\s*\). A quoted value is a literal;
       an unquoted value is a variable: store its name and set dynamic true. Otherwise dynamic false.
       Missing option = null.
     If a block is not closed (closed False): add an unparsed range [start, end] with reason
     "EXEC block not closed" and set parse_status partial.
  9. paragraphs: lines after the PROCEDURE DIVISION header. A header line is a code line whose
     stripped text matches ^[A-Z0-9][A-Z0-9-]*\.$ and is NOT one of EXIT CONTINUE GOBACK END-IF
     END-EVALUATE END-PERFORM END-READ END-EXEC END-CALL STOP NEXT SENTENCE; in fixed source_format
     it must also start within the first 4 characters of the cleaned text (area A). A line
     ^[A-Z0-9][A-Z0-9-]*\s+SECTION\.$ is also a header. If statements appear before the first header,
     create a paragraph named "(START)". Each paragraph: {id "para:<PGM>.<NAME>", name, line_start,
     line_end (line before the next header, or the last code line), events}.
  10. Walk each paragraph's code lines in order and produce events, conditions and calls.
     Skip lines that belong to an EXEC block, except the block's first line, which yields one
     event (kind sql or cics with ref = the block id). For a CICS block whose command is RETURN,
     also add an end event (how "CICS_RETURN"). Keep a stack of open constructs and an event
     counter seq (starting at 1 in each paragraph). under = the id of the innermost open
     condition (the current WHEN for an EVALUATE), else null.
       IF: ^\s*IF\s+(.+?)(?:\s+THEN)?\s*$ -> new condition {id cond:<PGM>.n, kind "IF", text,
         paragraph, parent (current innermost condition id or null), line_span [line, line]};
         push it.
       ELSE: nothing (its events stay under the same IF).
       END-IF: pop the nearest IF and set its line_span end to this line.
       EVALUATE: ^\s*EVALUATE\s+(.+) -> condition kind "EVALUATE", text = the subject; push.
       WHEN: if the top of the stack is an EVALUATE: new condition kind "WHEN", parent = the
         EVALUATE's id, text = the rest of the line; it becomes that EVALUATE's current WHEN
         (the previous WHEN's span ends on the line before).
       END-EVALUATE: pop it and close spans.
       PERFORM with a UNTIL: add a condition kind "UNTIL", text = the text after UNTIL, parent = the
         innermost condition. If the line has no paragraph target (inline perform), push it.
       Inline PERFORM (matches ^\s*PERFORM\s+(UNTIL|VARYING|WITH\s+TEST|\d+\s+TIMES|FOREVER)): push a
         construct, pop on END-PERFORM.
       A code line ending with "." (outside EXEC blocks) closes all open constructs (set span ends
         to that line). A paragraph boundary also closes everything (span end = previous line).
       Text rules: uppercase, strip a trailing ".", collapse spaces, cut to 120 chars.
     Events (all have seq, kind, line, under), emitted in this order per line:
       perform: ^\s*PERFORM\s+([A-Z0-9-]+) where the target is not UNTIL/VARYING/WITH/TEST/FOREVER
         and not numeric -> target, thru (THRU|THROUGH\s+([A-Z0-9-]+) or null), loop (line contains
         UNTIL, VARYING or TIMES)
       goto: ^\s*GO\s+TO\s+([A-Z0-9-]+) -> target (the first one)
       file_op: OPEN/CLOSE use statement_text and the known file names: in an OPEN, the words
         INPUT, OUTPUT, I-O, EXTEND set the current mode and each known file name that follows
         gets one event {op "OPEN", file, mode}; CLOSE gives {op "CLOSE", file, mode null} per
         file. ^\s*READ\s+X, ^\s*DELETE\s+X, ^\s*START\s+X -> file X. ^\s*WRITE\s+X and
         ^\s*REWRITE\s+X -> the file for record X from step 5 (if unknown, file = X).
       call: \bCALL\s+(?:(["'])([A-Z0-9#@$_-]+)\1|([A-Z][A-Z0-9-]*)) -> new item in calls[]
         {id call:<PGM>.n, target, dynamic (unquoted), args (names after USING in the joined
         statement, up to ON EXCEPTION / ON OVERFLOW / END-CALL / RETURNING / the final ".";
         drop BY REFERENCE|CONTENT|VALUE), paragraph, line}; event {ref = the call id}. If the
         target is ABEND, CEE3ABD or ILBOABN0 also add an end event (how "ABEND").
       display: ^\s*DISPLAY\s+(.+) -> text = the first quoted literal without quotes, else the first
         token; max 80 chars.
       error_check: SQLCODE (a condition line containing \bSQLCODE\b), FILE_STATUS (a condition line
         containing a status_var of a declared file), RETURN_CODE (\bRETURN-CODE\b on a condition
         line), INVALID_KEY (INVALID\s+KEY), AT_END (\bAT\s+END\b), ON_SIZE_ERROR (ON\s+SIZE\s+ERROR),
         ON_EXCEPTION (ON\s+(EXCEPTION|OVERFLOW)). Fields what, var (the variable name or null).
         For a condition line, emit it after the condition is pushed (so under = that condition).
       end: STOP\s+RUN -> "STOP_RUN"; GOBACK -> "GOBACK"; EXIT\s+PROGRAM -> "EXIT_PROGRAM".
     Event fields by kind: perform{target,thru,loop} goto{target} file_op{op,file,mode}
       sql{ref} cics{ref} call{ref} display{text} error_check{what,var} end{how}.
  11. Fill files[] fields: open_modes = modes from that file's OPEN events (unique, in order);
     operations = the ops among READ, WRITE, REWRITE, DELETE, START used on it (unique);
     lines = the lines of its file_op events (unique, sorted, max 20). access: if operations is
     non-empty: has_read = READ or START in operations, has_write = WRITE, REWRITE or DELETE in
     operations; else fall back to open_modes (INPUT -> read; OUTPUT/EXTEND -> write; I-O -> both).
     access = "read_write" if both, "read", "write", or "unknown".
  12. conditions[] = all conditions in id order. metrics {paragraphs, conditions, sql, cics, calls,
     lines}. Program keys in order: id, name, line_span, dialect, files, copybooks, data_items,
     linkage, sql, cics, calls, conditions, paragraphs, metrics.

  parse_data_items(code_lines) -> list: for each line matching
    ^\s*(\d{1,2})\s+([A-Z0-9][A-Z0-9-]*|FILLER)\b  with level in 01-49, 66, 77, 88, take the entry
    text (statement_text, max 4 lines, stop at the next level entry) and extract:
      pic: \bPIC(?:TURE)?\s+(?:IS\s+)?(\S+) without a trailing "."
      usage: the first of COMP-3 COMP-1 COMP-2 COMP-4 COMP-5 COMP COMPUTATIONAL-3 COMPUTATIONAL
             BINARY PACKED-DECIMAL DISPLAY INDEX POINTER that is not part of a longer name
             (not preceded or followed by a letter, digit or "-"), else null
      redefines: REDEFINES\s+([A-Z0-9-]+) ; occurs: OCCURS\s+(\d+) as int
      value: VALUE\s+(?:IS\s+)?("[^"]*"|'[^']*'|[^\s.]+) as written, max 40 chars
    Item: {name, level (int), pic, usage, redefines, occurs, value, line}. Skip FD/SD lines.

jcl_ir.py  ->  build_jcl_ir(content, rel_path, declared_names) -> (jcl_dict, unparsed_ranges)
  Statements: every code line starting with "//" matching ^//(\S*)\s+(\S+)\s*(.*)$ gives name, op,
  operands. If name is empty and op is not one of EXEC DD JOB PROC PEND INCLUDE SET IF ELSE ENDIF
  OUTPUT, the line is a continuation: append op + operands (no space) to the previous statement's
  operands. Lines not starting with "//" are ignored.
  - kind: "job" if a JOB statement exists, else "proc". name: the JOB name; else the PROC name;
    else declared_names[0]. id "job:<NAME>" or "proc:<NAME>". line_span = first and last "//" line.
  - Each EXEC starts a step; the DD statements after it (until the next EXEC or PEND) belong to it.
    step: {name (step name, or "STEP<order>" if empty), order (from 1), line_span, exec_kind, target,
    parm, cond, dds}. exec_kind "pgm" if operands match PGM=([A-Z0-9#@$]+) (target = that);
    else "proc" with target = (?:PROC=)?([A-Z0-9#@$]+) at the start of the operands.
    parm: PARM=('[^']*'|[^,\s]+) without quotes; cond: COND=(\([^)]*\)|[^,\s]+) else null.
  - dds[]: {ddname, dsn, disp, kind, access, inferred, line}. ddname = the DD name; if empty use the
    previous DD's name in the step (kind concat). dsn: DSN(?:AME)?=([^,\s]+) or null. disp:
    DISP=(\([^)]*\)|[^,\s]+) with parentheses and spaces removed (e.g. "MOD,DELETE") or null.
    kind/access, first matching rule wins:
      1 operands start with SYSOUT=          -> "sysout", "write"
      2 operands contain the word DUMMY      -> "dummy", null
      3 operands start with * or DATA        -> "inline", "read"
      4 the DD name was empty                -> "concat", "read" (or from DISP if present, rule 7)
      5 no DSN                               -> "other", null
      6 disp parts (split on ",") [1] == "DELETE" -> "delete", "write"
      7 first disp part (default "NEW" if no DISP): NEW -> "new","write"; MOD -> "output","write";
        SHR -> "input","read"; OLD -> "input","unknown"; else "other","unknown"
    inferred is always true.
  - includes[]: INCLUDE statements: {member (MEMBER=([A-Z0-9#@$]+)), line}.
  - If no JOB, PROC or EXEC statement is found the result is partial (reason "no JCL statements").
  Keys in order: kind, id, name, line_span, steps, includes.

copybook_ir.py  ->  build_copybook_ir(content, rel_path, declared_names) -> (dict, unparsed)
  {id "cpy:<declared_names[0] or file stem>", name, copies (every ^\s*COPY\s+["']?NAME line:
  {name, line}), data_items (parse_data_items on all code lines), declares_table (name from a
  block  EXEC SQL DECLARE <name> TABLE  found with find_exec_blocks, else null)}.

bms_ir.py  ->  build_bms_ir(content, rel_path, declared_names) -> (dict, unparsed)
  USE content.raw_lines (labels start in column 1). Skip lines starting with "*".
  mapset = first ^([A-Z0-9#@$]+)\s+DFHMSD\b ; maps = each ^([A-Z0-9#@$]+)\s+DFHMDI\b(.*) as
  {name, size ("24x80" from SIZE=\((\d+),(\d+)\) on the same line, else null), line};
  field_count = lines containing \bDFHMDF\b. id "map:<mapset>". If no mapset is found: partial
  (reason "no DFHMSD"), id "map:<file stem>". Keys: id, mapset, maps, field_count.

runner.py
  run_ir(inventory: dict, source_folder: str, output_dir: str, progress=None, should_stop=None)
    -> dict. For each entry in inventory["files"] (types and declared_names from the entry):
    read_file(os.path.join(source_folder, path)), build_file_ir(...), write
    <output_dir>/files/<path>.ir.json (json, indent 2, ensure_ascii False, utf-8; create folders).
    Call progress("IR <n>/<total>: <path>") per file; check should_stop() between files.
    Also write <output_dir>/ir_run.json: {schema_version "1.0", source_folder, inventory_file,
    generated_at (UTC ISO), complete (false if stopped), files: [{path, type, ir_file (relative to
    output_dir), parse_status, counts}]}. counts: program -> {paragraphs, sql, cics, calls,
    conditions}; jcl -> {steps, dds}; copybook -> {data_items, copies}; bms -> {maps, fields}; other
    types -> {}. Return the same dict.
  Output folder: workspace/stage2_outputs/<source-directory-name>_ir_<YYYYMMDD_HHMMSS>/

app.py / index.html
  - Under the inventory result add a section "Per-file IR" with a "Build IR" button, enabled only
    when a completed inventory exists. Input = the inventory the app already holds, or the newest
    workspace/stage1_outputs/*_inventory_*.json whose "complete" is true; source folder = its
    "source_folder" (show an error if the folder no longer exists).
  - Clicking it starts the background run (same mechanism as the inventory run): progress log
    (collapsible), Stop button (takes effect between files), results loaded into the same page.
  - Result: the output folder path, and a table File | Type | Parse status | Counts | IR file.
    Rows with parse_status "partial" get style="background:#fff3cd".

TESTS  (pytest, tmp_path; write files with write_text; helper line_of(lines, text) returns the
1-based number of the first line containing text. Build FileContent with read_file.)
  test_ir_cobol.py
   1. Program TESTPGM, 7 leading spaces on every line:
        IDENTIFICATION DIVISION.
        PROGRAM-ID. TESTPGM.
        ENVIRONMENT DIVISION.
        INPUT-OUTPUT SECTION.
        FILE-CONTROL.
            SELECT INFILE ASSIGN TO UT-S-INDD
                ORGANIZATION IS SEQUENTIAL
                FILE STATUS IS WS-IN-STATUS.
            SELECT OUTFILE ASSIGN TO UT-S-OUTDD.
        DATA DIVISION.
        FILE SECTION.
        FD  INFILE.
        01  IN-REC            PIC X(80).
        FD  OUTFILE.
        01  OUT-REC           PIC X(80).
        WORKING-STORAGE SECTION.
        01  WS-IN-STATUS      PIC XX.
        01  WS-BALANCE        PIC S9(9)V99 COMP-3 VALUE 0.
        01  WS-EOF            PIC X VALUE 'N'.
            88  AT-EOF        VALUE 'Y'.
            COPY ACCTREC.
            EXEC SQL INCLUDE SQLCA END-EXEC.
            EXEC SQL DECLARE ACCTCUR CURSOR FOR
                SELECT ACCT_NO, BALANCE FROM ACCOUNT
                WHERE STATUS = 'A'
            END-EXEC.
        LINKAGE SECTION.
        01  LS-PARM           PIC X(10).
        PROCEDURE DIVISION USING LS-PARM.
        MAIN-PARA.
            OPEN INPUT INFILE OUTPUT OUTFILE.
            PERFORM READ-PARA UNTIL AT-EOF.
            IF WS-IN-STATUS NOT = '00'
                DISPLAY 'BAD STATUS'
            END-IF.
            EXEC SQL OPEN ACCTCUR END-EXEC.
            EXEC SQL
                UPDATE ACCOUNT SET BALANCE = :WS-BALANCE
                WHERE ACCT_NO = :WS-ACCT
            END-EXEC.
            CALL 'SUBPGM' USING WS-BALANCE.
            CLOSE INFILE OUTFILE.
            GOBACK.
        READ-PARA.
            READ INFILE
                AT END MOVE 'Y' TO WS-EOF
            END-READ.
            WRITE OUT-REC FROM IN-REC.
      Expect: id "pgm:TESTPGM"; parse_status complete; linkage is_subprogram true, params
      ["LS-PARM"]; files INFILE (ddname INDD, organization SEQUENTIAL, status_var WS-IN-STATUS,
      open_modes ["INPUT"], operations ["READ"], access "read") and OUTFILE (ddname OUTDD,
      open_modes ["OUTPUT"], operations ["WRITE"], access "write"); copybooks ACCTREC with the
      right line, replacing false; sql ids sql:TESTPGM.1..4 with kinds include (include "SQLCA"),
      declare_cursor (cursor ACCTCUR, tables ["ACCOUNT"], access "read", paragraph null), open
      (tables ["ACCOUNT"], paragraph "MAIN-PARA"), update (tables ["ACCOUNT"], access "write",
      host_vars ["WS-BALANCE","WS-ACCT"]); calls: one, target SUBPGM, dynamic false, args
      ["WS-BALANCE"], paragraph MAIN-PARA; paragraph names ["MAIN-PARA","READ-PARA"]; MAIN-PARA
      event kinds ["file_op","file_op","perform","error_check","display","sql","sql","call",
      "file_op","file_op","end"] with the perform loop true and target READ-PARA, the display
      text "BAD STATUS", the error_check what "FILE_STATUS" and its "under" equal to the IF
      condition's id; READ-PARA kinds ["file_op","error_check","file_op"] (error_check what
      "AT_END"); conditions: UNTIL "AT-EOF" then IF "WS-IN-STATUS NOT = '00'" whose line_span ends on
      the END-IF line; data_items: WS-BALANCE (level 1, pic "S9(9)V99", usage "COMP-3", value "0"),
      AT-EOF (level 88, value "'Y'"), IN-REC (pic "X(80)"); dialect uses_sql true, uses_cics false;
      metrics paragraphs 2, conditions 2, sql 4, cics 0, calls 1.
   2. Conditions program CONDPGM (7 leading spaces):
        IDENTIFICATION DIVISION.
        PROGRAM-ID. CONDPGM.
        PROCEDURE DIVISION.
        MAIN-PARA.
            IF A > 1
                IF B > 2
                    PERFORM P1 THRU P2
                END-IF
            ELSE
                GO TO EXIT-PARA
            END-IF.
            EVALUATE TRUE
                WHEN X = 1
                    PERFORM P1
                WHEN OTHER
                    PERFORM P2
            END-EVALUATE.
            STOP RUN.
        P1.
            EXIT.
        P2.
            EXIT.
        EXIT-PARA.
            EXIT.
      Expect 5 conditions in order: IF "A > 1" (parent null), IF "B > 2" (parent = the first),
      EVALUATE "TRUE", WHEN "X = 1" and WHEN "OTHER" (both parent = the EVALUATE). Events in
      MAIN-PARA: perform P1 thru P2 under the second IF; goto EXIT-PARA under the first IF;
      perform P1 under the first WHEN; perform P2 under the second WHEN; end STOP_RUN under null.
      The inner IF's span ends on the first END-IF line and the outer IF's on the second.
      Paragraph names ["MAIN-PARA","P1","P2","EXIT-PARA"].
   3. CICS program ONLPGM (7 leading spaces): IDENTIFICATION DIVISION / PROGRAM-ID. ONLPGM. /
      PROCEDURE DIVISION. / MAIN-PARA. / then
            EXEC CICS RECEIVE MAP('SGNA')
                 MAPSET('SGN00')
            END-EXEC.
            EXEC CICS XCTL
                 PROGRAM(WS-NEXT)
            END-EXEC.
            EXEC CICS RETURN TRANSID('CC00')
                 COMMAREA(WS-COMM)
            END-EXEC.
      Expect cics: (RECEIVE MAP, map SGNA, mapset SGN00, dynamic false), (XCTL, program WS-NEXT,
      dynamic true), (RETURN, transid CC00, dynamic false); event kinds ["cics","cics","cics","end"]
      with the end how "CICS_RETURN".
   4. A program with a CBL card on the first line ("CBL OPTIMIZE(FULL)") and a COPY ... REPLACING
      statement: dialect cbl_cards non-empty, copy_replacing true.
   5. A program with no PROCEDURE DIVISION: parse_status "partial", an unparsed range with reason
      "no PROCEDURE DIVISION", paragraphs [].
   6. An unclosed "EXEC SQL SELECT 1 FROM X" with no END-EXEC: parse_status "partial" and an
      unparsed range with reason "EXEC block not closed".
  test_ir_jcl.py
   1. Job:
        //DAILYJOB JOB (ACCT),'DAILY RUN',CLASS=A
        //PREPARE  EXEC PGM=IEFBR14
        //OLDOUT   DD DSN=BANK.OUT,DISP=(MOD,DELETE)
        //MAIN     EXEC PGM=TRANPROC,
        //         PARM='PROD'
        //INFILE   DD DSN=BANK.TRANS,DISP=SHR
        //OUTFILE  DD DSN=BANK.TRANOUT,DISP=(NEW,CATLG)
        //         DD DSN=BANK.TRANOUT2,DISP=SHR
        //SYSOUT   DD SYSOUT=*
        //SYSIN    DD *
        //STEP3    EXEC MYPROC
        //         INCLUDE MEMBER=INC1
      Expect kind "job", id "job:DAILYJOB"; 3 steps: PREPARE (pgm IEFBR14), MAIN (pgm TRANPROC,
      parm "PROD"), STEP3 (exec_kind proc, target MYPROC); PREPARE dd OLDOUT: dsn BANK.OUT,
      disp "MOD,DELETE", kind "delete", access "write", inferred true; MAIN has 5 dds: INFILE
      (input, read), OUTFILE (new, write), a concat dd with ddname "OUTFILE" (access read),
      SYSOUT (sysout, write, dsn null), SYSIN (inline, read); includes [{member INC1, line 12}].
   2. Proc: lines "//MYPROC   PROC", "//STEP1    EXEC PGM=IEFBR14",
      "//DD1      DD DSN=&HLQ..DATA,DISP=SHR" -> kind "proc", id "proc:MYPROC", 1 step, dd dsn
      "&HLQ..DATA" kind input.
   3. A file typed jcl with no statements -> partial with reason "no JCL statements".
  test_ir_copy_bms.py
   1. Copybook (declared_names ["ACCTREC"]; 7 leading spaces):
        01  ACCT-RECORD.
            05  ACCT-NUMBER     PIC X(10).
            05  ACCT-BALANCE    PIC S9(9)V99 COMP-3.
            COPY SUBREC.
      -> id "cpy:ACCTREC", 3 data_items, copies [{name SUBREC, line 4}], declares_table null.
   2. A DCLGEN-style copybook with "EXEC SQL DECLARE ACCOUNT TABLE ( ACCT_NO CHAR(10) NOT NULL )
      END-EXEC." and a level-01 item -> declares_table "ACCOUNT".
   3. BMS lines:
        MAPSET1  DFHMSD TYPE=&SYSPARM,MODE=INOUT,LANG=COBOL
        MAP1     DFHMDI SIZE=(24,80)
        FIELD1   DFHMDF POS=(1,1),LENGTH=10
                 DFHMDF POS=(2,1),LENGTH=5
                 DFHMSD TYPE=FINAL
      (continuation lines start with 9 spaces) -> id "map:MAPSET1", mapset "MAPSET1",
      maps [{name MAP1, size "24x80", line 2}], field_count 2.
  test_ir_run.py
   1. In a tmp folder write: the TESTPGM program, the job from test_ir_jcl 1, the copybook, the
      BMS file and a markdown file ("# T", "- a", "- b", a fenced block). Run build_inventory on the
      folder, then run_ir into a tmp output dir. Expect ir_run.json with 5 files and complete true;
      every IR file exists under files/<path>.ir.json; the markdown file's IR has a header but no
      body key; the program IR has "program" with paragraphs.
   2. should_stop returning true after the first file -> complete false and fewer than 5 files.
   3. Monkeypatch the function that builds the program IR to raise: that file's IR has
      parse_status "partial" and an unparsed range reason starting "extractor error", and the
      other files are still produced.

DO NOT
  - build the consolidated IR, graph, entry points or order (next increment).
  - store source text beyond the limits above, call an LLM, or add libraries.
  - change Stage 1 modules/tests or the Stage 1 JSON/sorted-folder behavior.
  - add keys that are not listed.

HOW I WILL RUN IT (Windows PowerShell)
  python -m pytest
  python app.py
How to check it

All tests pass, including the Stage 1 tests.
Run Stage 1 on the banking repo, then click Build IR. Open workspace/stage2_outputs/<folder>_ir_<time>/files/.
JCL/EOD.jcl.ir.json should show steps running RECONCIL, INTCALC and IEBGENER, and JCL/DAILY.jcl.ir.json should include a step running TRANPROC.
COBOL/INTCALC.cbl.ir.json should show the ACCOUNT table in its SQL entries, with paragraphs and events in source order.
Send me one program IR and one JCL IR that look wrong, and I'll point out which rule needs adjusting.
I expect the most likely problems to be SELECT statement joining and paragraph detection on real fixed-format files, so please check those two first.

I dont understnad..... Why are we creating an ir. What is it. What contribution its gonna make. Explain with example


Ran 2 commands
Ran 2 commands
An IR (intermediate representation) is a fact sheet about the code, written as structured data instead of code. A program, for instance, becomes a list of what it is, what it touches and what it calls, with line numbers. It's the same kind of information a person would write down while reading the code, but a script collects it exactly and the same way every time.

Example from your banking repo

The code in INTCALC.cbl is about 140 lines. In the middle of it:

200-PROCESS-INTEREST.
    EXEC SQL OPEN INTEREST_CURSOR END-EXEC.
    PERFORM UNTIL SQLCODE NOT = 0
        PERFORM 210-CALCULATE-INTEREST
        PERFORM 220-UPDATE-ACCOUNT-INTEREST ...
Its IR says the same thing as facts:

program INTCALC
  writes report file  INTRPT   (line 130)
  reads table         ACCOUNTS (line 67-69)
  updates table       ACCOUNTS (line 104)
  inserts into table  TRANSACTIONS (line 114)
  paragraphs in order: 000-MAIN → 100-INIT → 200-PROCESS
     (200 performs 210, 220, 230 in a loop until SQLCODE ≠ 0)
The job files get the same treatment. DAILY.jcl becomes: step MAIN runs TRANPROC and creates USER.TRANOUT, and step EODPROC runs RECONCIL, which reads USER.TRANOUT.

What that makes possible

Understanding. A newcomer can see "the daily job starts here, runs these programs in this order, and touches these tables" without reading all the code.
Finding connections nobody wrote down. Notice that EOD.jcl also runs RECONCIL and reads USER.TRANOUT, which DAILY creates. The two jobs never mention each other, but the IR links them through that dataset. That kind of link is what decides how to cut the codebase into modules: those two jobs must stay together or have a defined interface.
Conversion order. The IR knows INTCALC needs the ACCOUNTS and TRANSACTIONS tables defined first, and DAILY's output before EOD. So the tool can say "convert the data layer first, then DAILY's programs, then EOD."
Safe use of the LLM. The LLM would later get one paragraph at a time plus these facts, instead of a whole 5,000-line codebase. The facts come from code, so they're repeatable and can be checked, which an LLM's reading of a huge file can't promise.
In short, Stage 1 told us which files exist, and the IR tells us what is inside each one and how they connect. The module splitting and the order are then computed from the IR.

Does that make it clear? If so, I can walk through how one of the IR files looks end to end.

Files hidden when shared
Bu tthe ir we are making is not doing this....... Its just a dumb regex that checks oh a if statement so make block, and add the remaing thin as text, i wnat to 7ndeartand how are we goin to use this ir to split the app

You're partly right. The IR is pattern-based, and your screenshots do show real weaknesses. But most of what you see (the blocks, conditions and paragraph events) is not what splits the app. Here are both halves.

How the IR is used to split the app

Splitting uses only a handful of facts, and your screenshots contain some of them. For CUPO003:

It links to CIPTMON (several times) and to CUPOGDLG.
It works with temporary-storage queues (DELETEQ TS).
Those become edges in the graph:

pgm:CUPO003 --links--> pgm:CIPTMON
pgm:CUPO003 --links--> pgm:CUPOGDLG
pgm:CUPO003 --uses--> queue QUEUENAME
A module is then everything reachable from an entry point by following edges (calls, links, XCTL, COPY, runs), plus anything that shares a table, file or queue with another entry point. That's all the splitting reads. The IF blocks, paragraph events and conditions are for understanding and for the LLM's business-rule step. They have no effect on where the cuts go.

So what matters is one question: are the edges right? A missing edge silently puts two pieces that belong together into different modules.

What your screenshots show that is wrong

LINK entries with "program": null. On line 8044, a LINK was found but its target wasn't. That is a missed edge. My guess is the source writes it in a form the pattern doesn't expect, for example PROGRAM (X) with a space, but I need to see the line to be sure.
QUEUENAME marked dynamic. The queue name sits in a variable, so we can't tell which queue is used. Programs that share a queue are coupled, so this hides real links.
How to make it smarter without a heavy parser

Fix the pattern misses (the null targets) first. They're bugs, not limits.
Resolve variables cheaply. Most dynamic targets are set earlier in the program with MOVE 'XYZ' TO VAR or a VALUE 'XYZ' clause. A small lookup can recover candidate values and mark the edge "resolved from MOVE" or "ambiguous, several values".
Use the LLM only for leftovers. Unresolved cases get a small snippet, and the answer is checked against the list of known programs before it's accepted.
We measure progress by how many calls, links, copies and SQL tables end up resolved to a real target.

Can you paste lines 8040 to 8048 of the CUPO003 source? I'll find out why that LINK came out empty.

Files hidden when shared
That screenshot answers the QUEUENAME question, and it shows the "dynamic" flag was correct, not a bug.

QUEUENAME (line 281) is a group made of two 4-character fields: QUEUENAME-TRANS and QUEUENAME-TERM. So the queue name is built at run time from a transaction ID and a terminal ID. The IR can't know the name from the DELETEQ TS line alone. There's a similar group, 244-TSNAME with 244-TRANS and 244-TERM, right above it.

That name pattern is probably a per-terminal scratch queue, meaning one queue per user session. If so, it is private working storage and not a data link between programs. We would wrongly merge modules if we treated every queue name as shared data.

What the IR should do with it (cheap, no LLM):

For a dynamic queue name, look up the group in the data items. If the variable is a group, find which fields get filled by MOVE statements and record the pattern, for example QUEUENAME = <transaction id> + <terminal id>.
If the pieces come from the CICS system fields for the current transaction and terminal (EIBTRNID, EIBTRMID), mark the queue as session-private. It then doesn't count as shared data when we decide what belongs together.
If the pieces come from somewhere else, mark it ambiguous and list it for review.
I'm guessing at those MOVE sources from the field names. I haven't seen the statements, so this needs checking against the code.

Also worth noting from this screenshot: the file is fixed-format with sequence numbers in columns 1-6. It mixes lowercase and uppercase (pic x(20) next to PIC X(04)) and has names that start with digits (244-TRANS). Our patterns are case-insensitive and allow leading digits, so they should handle it, but real files like this are what will break rules first.

Could you paste the lines that fill the queue name (search for TO QUEUENAME-), and still lines 8040-8048 for the LINK with the empty target?

Lets move to next increment. What is it

Per the plan, the next one is Increment 5: the consolidated IR. It joins the per-file IRs into one connected picture of the whole project.

What it does
It reads the per-file IRs and produces one project_ir.json, which holds the connections between files rather than the details inside them. This is where the project starts to answer your supervisor's questions.

Input: the per-file IR folder from Increment 4 (ir_run.json plus the files), and the Stage 1 inventory.

How it works, in order

Nodes: one for every program, copybook, JCL job and proc, BMS map, DB2 table and dataset found in the facts, each with a status (defined, system, gap or dynamic).
Edges: every COPY, CALL, LINK, XCTL, JCL step, map use and SQL or file access becomes a typed arrow with its file and line, resolved against the nodes.
The data join: a program's file name (its ddname) is matched to the DD in the JCL step that runs it, which gives the program → dataset reads/writes edge. This is what connected DAILY and EOD through USER.TRANOUT in the earlier example.
Entry points: every job, online transaction and unreferenced program, with its ordered steps, everything it reaches, and the data it touches.
Cycles and conversion order: mutually dependent programs are grouped into one unit, and everything is sorted into waves from least to most dependent. Data stores come first.
Coupling: for each pair of entry points, what code and data they share. Shared writes mean "probably one module".
Quality block: the resolved-to-unresolved edge ratio and a list of caveats, so a bad result is visible.
Output: project_ir.json in a new output folder, plus a page showing entry points, the order, gaps and the quality numbers. The module fields stay empty, because splitting is Increment 8.

How we'll check it on the banking repo

The gaps are ACCTREC, ERRHDLR, TRANREC and TRANPROC, and SQLCA is system.
USER.TRANOUT is written by DAILY's TRANPROC step and read by RECONCIL, in both DAILY and EOD.
INTCALC reads and updates ACCOUNTS and inserts into TRANSACTIONS, so the tables sit in wave 0.
One dependency: the graph is only as good as the edges Increment 4 produced, and your CUPO003 run showed some LINK calls with an empty target. I'd fix those first or alongside, since a missed edge silently splits things that belong together.

Do you want the Increment 5 prompt now, or the Increment 4 fixes first?

think about ot in detail. what information should be there in that ir. it should have everything needed for next steps as well as for documnets

I'd design it by working backwards from the questions each later step has to answer, so every field earns its place.

The questions it must answer

Understanding and documents: What is the system made of? Where does each activity start? What does it read and write? What's missing? How does a user move through the screens?
Conversion order: What must exist before X? Are there cycles?
Splitting: What does entry point E need to run? What do E and F share?
Business rules: For program P, who calls it, what data does it get, and what are the record layouts and tables?
What goes in it (tags show who uses it: D documents, O order, S splitting, R business rules)

Project profile (D). Source, run info, counts per file type, total lines, technology flags (batch, CICS, DB2), the largest and most complex programs, and a complete flag.
Nodes (all). One per program, copybook, job, proc, screen map, table, dataset, queue, transaction and system utility. Every node has id, kind, name, defined_in and status (defined, system, gap or dynamic). Each kind also gets a short card:
Program: lines, number of paragraphs and conditions (complexity), mode (batch, online, subprogram), parameters, callers, callees, copybooks, the stores it touches with access mode, screens used, which error checks it uses, and its header comment.
Dataset, table, queue: producers, consumers, readers, writers, the record layout (found via the program's file record), and lifetime (for example deleted at the start of a job). For queues, the scope: session-private (name built from transaction and terminal), shared, or ambiguous.
Job: its steps in order.
Copybook: who uses it and how (file record, working storage, linkage, or DB2-generated table layout).
Transaction: where it's started from and which program it likely runs (inferred).
Edges (all). from, to, kind, file, line, the paragraph or JCL step, status, access, inferred, the condition it sits under, and for dynamic targets candidates plus how they were found (for example "MOVE literal at line 412").
Entry points (D, S).
The trigger, a confidence level, and ordered steps with the data read and written.
Everything reachable, and the data touched.
Pointers into the per-file IR, so a paragraph-by-paragraph flow can be drawn.
An empty summary for the LLM.
Online flows (D). Screen → program → next program (XCTL, LINK, RETURN TRANSID) in order. This is what a sequence diagram needs.
Data view (D, S). Each store with its producers and consumers, a CRUD matrix (program × store), and an index of record layouts.
Interfaces (R, D). For each called program: parameters with their PIC clauses, who calls it with which arguments, and the COMMAREA passed.
Catalogs (D). All user messages, a per-program error-handling summary, the job and step table, and the screen inventory.
Gaps with impact (D, O). Each missing item, who references it, and which entry points and units are blocked by it.
Cycles and conversion order (O). Waves of units, each with its size in lines and complexity, so effort can be estimated.
Coupling, modules, shared, boundary edges (S). As in the earlier schema. Modules stay empty until splitting.
Quality (all). Resolved versus unresolved edges, unparsed files, a list of dynamic references and whether they were resolved, and caveats.
Small additions needed in the per-file IR (I'd fold these into the Increment 4 fixes)

section on each copybook (FILE, WORKING-STORAGE, LINKAGE), to classify layouts.
commarea on CICS LINK, XCTL and RETURN entries.
candidates on dynamic calls and CICS targets, from MOVE 'X' TO var and VALUE clauses.
header_comment per program and a one-line comment above each paragraph. In real shops (your Danish code, for example) most of the business meaning sits in comments, and the reader currently drops them.
columns on each SQL statement, for the data dictionary.
What I'd leave out: copies of source text, field-level data lineage, and the LLM-written text. All of that comes in later stages.

Question: should these five additions go into the Increment 4 fixes together, or do you want to pick which ones matter for now?

give me the copilot prompt as always

Here's the Increment 5 prompt. It has two parts. Part A adds the few facts to the per-file IR that the consolidated IR needs (copybook section, COMMAREA, candidate values for dynamic targets, queue scope, comments, SQL columns, file record names). It also fixes the empty LINK target by making the option pattern whitespace-tolerant and logging any target that is still missing in issues[], which will show us the exact line if the cause is something else. Part B builds the consolidated project_ir.json.

Two deliberate changes from the earlier schema: edges are aggregated (one edge per from, to and kind, with up to 10 refs[]), because real programs repeat the same table or link hundreds of times, and per-file IR moves to version 1.1. After Copilot finishes, re-run Build IR on your folders, then Build project IR.

You are a programmer who writes exactly what is specified below. Do not add features,
files, classes, config, logging, or libraries that are not listed. If something is
unclear, choose the simplest option and add nothing extra. Keep the code easy to read:
short functions, clear names, a one-line docstring on each function. Never use an LLM.

FIRST: read app.py, templates/index.html, stages/stage1_inventory/*, stages/stage2_ir/*
and the existing tests. Keep all Stage 1 and per-file IR behavior unless this prompt says
otherwise. Reuse the existing patterns for background runs, per-file/phase progress
messages, the Stop button and same-page result loading. Check the real function names
before using them. Existing tests must still pass; if one fails only because of a new key
or the new schema_version, update that test minimally.

GOAL
(A) Extend the per-file IR with a few facts the next step needs.
(B) Build ONE consolidated project_ir.json from all per-file IRs: nodes, typed edges,
    entry points with ordered steps, cycles, conversion order (least to most dependent),
    data view, interfaces, catalogs, gaps with impact, coupling between entry points,
    and a quality block. Splitting into modules is a LATER step: the module fields stay empty.

=====================================================================
PART A - ADDITIONS TO THE PER-FILE IR  (edit stages/stage2_ir/*)
=====================================================================
Set schema_version to "1.1" in every per-file IR header (update tests that assert "1.0").
Add these keys to the program IR. Keep existing keys and their order; new keys go where stated.

A1  copybooks[].section  (new key after "replacing")
    The section where the COPY statement sits: "ENVIRONMENT", "FILE", "WORKING-STORAGE",
    "LOCAL-STORAGE", "LINKAGE" or "PROCEDURE"; null if unknown. Track the current section while
    walking code lines: ^\s*ENVIRONMENT\s+DIVISION -> ENVIRONMENT; ^\s*(FILE|WORKING-STORAGE|
    LOCAL-STORAGE|LINKAGE)\s+SECTION -> that name; ^\s*PROCEDURE\s+DIVISION -> PROCEDURE.

A2  files[].record  (new key after "logical_name")
    The first 01-level record name that follows this file's FD (from the existing FD mapping), else null.

A3  CICS options: whitespace-tolerant extraction + commarea
    Replace the option regex with:  (?<![A-Z0-9-])KEY\s*\(\s*(['"]?)([^'")\s]+)\1\s*\)
    (so "PROGRAM ( 'X' )", "PROGRAM(X)" and lowercase all work). Quoted value = literal
    (dynamic false); unquoted = variable name (dynamic true). Add cics[].commarea (new key
    after "queue"): the COMMAREA( ) value or null. Also support the options DATASET( ) for file.

A4  cics[].candidates and cics[].queue_scope  (new keys after "dynamic")
    candidates: [] unless the item is dynamic. For a dynamic item, candidates =
    find_candidates(code_lines, data_items, <the variable name>) using the variable of the
    first dynamic option in this order: program, map/mapset, file, queue.
    queue_scope: null unless the command's first word is READQ, WRITEQ or DELETEQ (TS or TD):
      - queue is a literal -> "shared"
      - queue is a variable -> let V = the variable (the part before any OF). Let CH = the names
        of V's child data items (items after V in data_items with a greater level, up to the next
        item with level <= V's level; empty if V is elementary). If the program has a MOVE
        statement (use statement_text) of the form MOVE EIBTRNID|EIBTRMID TO <one or more names>
        where any name is V or in CH -> "session_private".
        Else if candidates is non-empty -> "shared". Else "unknown".

A5  calls[].candidates  (new key after "dynamic"): same as A4 for dynamic calls, using the
    call's variable name; [] for literal targets.

    find_candidates(code_lines, data_items, var) in common.py or cobol_ir.py -> list of
    {value, line, how}:
      - how "move": every MOVE statement (statement_text) matching
        ^MOVE\s+(["'])(.*?)\1\s+TO\s+(.+)$ where the TO list (split on whitespace and commas,
        ignore the word OF and the name after OF) contains var. value = the literal, trimmed,
        uppercased, max 40 chars; line = the statement's first line.
      - how "value": the data item named var whose value starts with a quote: value = text
        inside the quotes, uppercased; line = its line.
      Unique by value (first occurrence), max 10, ordered by line.

A6  program.header_comment (new key after "name") and paragraphs[].comment (new key after "name")
    Use content.raw_lines (original line n = raw_lines[n-1]). A raw line is a comment line when:
    fixed source_format -> len >= 7 and line[6] in "*/" ; free -> line.lstrip() starts with "*>".
    Comment text = fixed: line[7:72].strip() ; free: text after "*>" stripped. Ignore comment
    lines whose text is empty or only made of the characters * - = _ # . (banners).
    header_comment: all comment texts from raw line 1 up to the line of PROGRAM-ID plus 40, but
    never beyond the PROCEDURE DIVISION line; joined with single spaces, max 300 chars; null if none.
    paragraph comment: starting at the line above the paragraph header, walk upward over blank raw
    lines and comment lines (max 8 lines) and stop at the first other line; reverse and join with
    single spaces, max 200 chars; null if none.

A7  sql[].columns  (new key after "tables")
    select / declare_cursor: the text between SELECT [DISTINCT|ALL] and the first INTO or FROM at
    parenthesis depth 0; split on commas at depth 0; per part: cut at " AS ", strip; skip parts
    starting with ":"; keep "*" as "*". insert: split the contents of  INSERT INTO <t> ( ... )  on
    commas. update: the text after SET up to WHERE (or the end), split on commas at depth 0, keep
    the text before "=" of each part. All other kinds: []. Uppercase, max 60 items, each max 60 chars.

A8  program.issues  (new key after "conditions"): list of {kind, line, detail}.
    kind "cics_target_missing": a CICS item whose command is LINK, XCTL or LOAD and whose program is
    null; line = its line; detail = the first 80 chars of the block text. Nothing else for now.

Part A tests (tests/test_ir_additions.py; 7 leading spaces on COBOL lines):
  1. COPY ACCTREC inside WORKING-STORAGE -> section "WORKING-STORAGE"; a COPY inside LINKAGE ->
     "LINKAGE"; a COPY after PROCEDURE DIVISION -> "PROCEDURE".
  2. EXEC CICS LINK PROGRAM ( 'CIPTMON' ) COMMAREA(WS-COMM) END-EXEC -> program CIPTMON,
     commarea WS-COMM, dynamic false. Same with the options on separate lines.
  3. EXEC CICS LINK END-EXEC with no PROGRAM -> program null and program.issues has one item
     kind "cics_target_missing" with the right line.
  4. Dynamic call: 01 WS-PGM PIC X(8) VALUE 'SUBC'. then MOVE 'SUBA' TO WS-PGM. and
     MOVE 'SUBB' TO WS-PGM. then CALL WS-PGM. -> calls[0].dynamic true and candidates values
     ["SUBC","SUBA","SUBB"] sorted by line, hows ["value","move","move"]. A literal CALL 'X' -> [].
  5. Queue scope: groups  05 QUEUENAME. / 10 QUEUENAME-TRANS PIC X(4). / 10 QUEUENAME-TERM PIC X(4).
     EXEC CICS DELETEQ TS QUEUE(QUEUENAME) END-EXEC -> dynamic true. With
     MOVE EIBTRNID TO QUEUENAME-TRANS. in the program -> queue_scope "session_private"; without the
     MOVE -> "unknown"; with only MOVE 'ABCD' TO QUEUENAME-TRANS... -> still "unknown" (candidates are
     only found for var itself) ; QUEUE('MYQ') -> "shared"; a non-queue command -> null.
  6. Comments: a fixed-format program with "      * PAYROLL POSTING" above PROGRAM-ID -> header_comment
     "PAYROLL POSTING"; a comment line "      * CALCULATE TAX" directly above a paragraph header ->
     that paragraph's comment "CALCULATE TAX"; a banner line "      *****" is ignored.
  7. SQL columns: SELECT A, B AS X FROM T INTO ... -> ["A","B"]; INSERT INTO T (C1, C2) VALUES (...)
     -> ["C1","C2"]; UPDATE T SET C1 = :X, C2 = 5 WHERE K = 1 -> ["C1","C2"].
  8. files[].record: FD INFILE. followed by 01 IN-REC. -> record "IN-REC".

=====================================================================
PART B - CONSOLIDATED PROJECT IR
=====================================================================
NEW FILES
  stages/stage3_project_ir/__init__.py
  stages/stage3_project_ir/loader.py     load_ir_run(ir_dir) -> (meta, files)
  stages/stage3_project_ir/graph.py      nodes + edges
  stages/stage3_project_ir/flows.py      entry points, cycles, conversion order
  stages/stage3_project_ir/views.py      profile, data view, interfaces, catalogs, gaps, coupling
  stages/stage3_project_ir/quality.py    quality block
  stages/stage3_project_ir/builder.py    build_project_ir(files, meta, progress=None, should_stop=None)
  stages/stage3_project_ir/runner.py     run_project_ir(ir_dir, output_root, progress=None, should_stop=None)
  tests/ir_fixtures.py, tests/test_project_ir.py
EDIT app.py, templates/index.html

CONVENTIONS
- Keys snake_case, in the order written. Names uppercased. Lines are original 1-based lines.
- Unknown = null, empty = []. Never guess. No source text is stored.
- Node status: "defined" | "system" | "gap" | "dynamic" | "external" | "unmapped"
- Edge status: "resolved" | "system" | "gap" | "dynamic" | "external"
- Sort every list that has no stated order: nodes by id, edges by (from, to, kind), others by name/id.

loader.py
  load_ir_run(ir_dir): read <ir_dir>/ir_run.json -> meta (keep source_folder, generated_at,
  complete); for each entry read <ir_dir>/<ir_file> -> files = {path: ir_dict}. Skip a missing file
  with a warning item in meta["load_warnings"].

graph.py
  build_nodes(files) -> (nodes: dict id->node, index: dict, duplicates: list)
  A node is {id, kind, name, defined_in, status, card}. card starts as {} and is filled later.
  Defined nodes, from the files in path order (the first file wins for a repeated id; the others
  go to duplicates as {id, files[]}):
    program body    -> "pgm:<NAME>"   kind "program", defined_in = path, status "defined"
    copybook body   -> its id "cpy:<NAME>"     kind "copybook"
    jcl body        -> its id "job:<NAME>" (kind "jcl_job") or "proc:<NAME>" (kind "jcl_proc")
    bms body        -> "map:<MAPSET>" kind "bms_map"; index.map_names[name] = id for the mapset
                       and every map name.
  A copybook with declares_table creates a table node (below) with layout_copybook = its id.
  Other nodes are created while building edges, through ensure_node(nodes, id, kind, name, status,
  defined_in=None): never downgrade an existing "defined" node.
    table       "tbl:<NAME>"  kind "table", status "external". NAME = the part after the last "."
                of the SQL table name; the other spellings go to node.qualified_names[].
    dataset     "ds:<DSN>"    kind "dataset", status "external"; temporary = DSN starts with "&&".
    unmapped dd "dd:<DDNAME>" kind "dataset", status "unmapped".
    CICS file   "cf:<NAME>"   kind "cics_file", status "external".
    queue       "q:<NAME>"    kind "queue", status "external" (literal queue names only).
    transaction "tx:<ID>"     kind "transaction", status "external".
    unknown     "dyn:<PGM>.<VAR>" kind "unknown_target", status "dynamic".
    system/gap  program "pgm:<N>", copybook "cpy:<N>", proc "proc:<N>", map "map:<N>" with status
                "system" (name in SYSTEM_NAMES or starting with a SYSTEM_PREFIXES item, imported
                from stages.stage1_inventory.linker) or "gap".
  Resolution order for any referenced program/copybook/proc/map name N (uppercased): defined node of
  the right kind -> use it; else system -> system node; else gap node.

  build_edges(files, nodes, index) -> (edges, dynamic_refs, info)
  Make raw edges, then aggregate. A raw edge: {from, to, kind, status, access, inferred, via,
  step, context, variable, ref: {file, line, paragraph, condition, section?, args?, commarea?, parm?}}.
  condition = the "under" of the event that references the item (map id -> under built from every
  paragraph's events that have "ref"); null if none. paragraph = the item's paragraph.
  Edge status: target node status defined/external/unmapped -> "resolved" (kind "starts" -> "external");
  system -> "system"; gap -> "gap"; dynamic -> "dynamic".
  Aggregate by (from, to, kind, status, access, inferred, via, step, context, variable) into one
  edge: keys from, to, kind, status, access, inferred, via, step, context, variable, count, refs
  (the first 10 refs in file/line order). Edge keys in exactly that order.

  PROGRAM edges (from "pgm:<NAME>"):
   - copybooks[]            -> kind "copies" to the copybook (ref has section)
   - sql[] kind include     -> kind "includes" to the copybook named in include
   - sql[] with tables and access "read"/"write" -> one edge per table: kind "reads"/"writes",
                              access "read"/"write"; dynamic sql: no edge, add a dynamic_refs item
   - calls[]                -> kind "calls"; ref has args
   - cics LINK -> "links", XCTL -> "xctl" (ref has commarea); RETURN with a transid -> kind "starts"
     to tx:<ID> ; SEND MAP / RECEIVE MAP -> "uses_map" to the map named by mapset (else map), resolved
     through index.map_names (defined) else a gap map node
   - cics READQ/WRITEQ/DELETEQ with a literal queue -> "reads" (READQ) / "writes" (WRITEQ, DELETEQ)
     to q:<NAME>, access read/write
   - cics file commands (command word READ, STARTBR, READNEXT, READPREV, ENDBR, RESETBR -> read;
     WRITE, REWRITE, DELETE, UNLOCK -> write) with a literal file -> "reads"/"writes" to cf:<NAME>
  DYNAMIC TARGETS (calls, links, xctl, maps, files, queues): the item has dynamic true.
   - queue with queue_scope "session_private": no edge; no dynamic_refs item; count it in the
     program card private_queues.
   - candidates non-empty: one edge per candidate value (resolved with the same rules as a literal),
     inferred true, via "candidates", variable = the variable name; plus one dynamic_refs item.
   - no candidates: one edge to the node "dyn:<PGM>.<VAR>" (status "dynamic"), plus a dynamic_refs
     item. Exception: a queue with scope "unknown" and no candidates gets NO edge (unknown private
     or shared), only the dynamic_refs item.
   dynamic_refs item: {node, kind (call|link|xctl|map|file|queue|sql), variable, scope, line,
   candidates: [values], resolved: bool (true if at least one candidate exists)}.

  JCL edges (from the job/proc node J; iterate steps in order):
   - exec_kind "pgm": resolve the target program -> edge "runs_program" (J -> program), step = the
     step name, ref line = step line_span[0], ref parm. exec_kind "proc": resolve the proc ->
     "runs_proc". Save info.step_targets[(J, step_name)] = target node id.
   - includes[]            -> "includes" (J -> proc named by member; gap if missing)
   - DATA JOIN. For a step that runs a DEFINED program P with an IR: for every P.files[] item with a
     ddname, find the step's DD with the same ddname (case-insensitive). If found and it has a dsn:
     dataset node ds:<DSN>; edges P -> ds with step, context = J, via "dd_join": program access
     "read" -> one "reads" edge; "write" -> one "writes"; "read_write" -> both; "unknown" -> use the
     DD's access (read/write/unknown); if still unknown: one "reads" edge with access "unknown",
     inferred true. inferred is false when the program access was known. If the DD has no dsn
     (SYSOUT, DUMMY, in-line) -> no edge. If the step has no DD for that ddname -> add a caveat
     "ddname <D> of <P> has no DD in step <S> of <J>" to info.caveats.
   - For a step whose target is NOT a defined program (system, gap or dynamic) or is a proc: for
     each DD with a dsn: edge J -> ds:<DSN>, kind "writes" if the DD access is "write", else "reads"
     (access as in the DD; unknown -> "reads" with access "unknown"), inferred true, via "disp",
     step = the step name.
   - Record info.runs[P] = list of (J, step) for every step that runs a defined program.
  After all JCL is processed: for every defined program with NO entry in info.runs and with
  files[] ddnames: node "dd:<DDNAME>" (status "unmapped") and a "reads"/"writes" edge by the program's
  access rules above (via "dd_join", inferred true, context null).

flows.py
  build_entry_points(nodes, edges, files) -> list
  Control kinds CODE = {copies, includes, calls, links, xctl, runs_program, runs_proc, uses_map}.
  CONTROL = {calls, links, xctl, runs_program}.
  1. jcl_job: one entry point per node of kind "jcl_job".
  2. Root units: build the graph of DEFINED program nodes with edges of kind calls/links/xctl
     (from program to program). Compute strongly connected components (iterative Tarjan). A component
     is a ROOT UNIT when no edge of kind calls/links/xctl comes from a program outside the component
     AND no member has an inbound runs_program edge. Per root unit one entry point:
       kind "online" if any member has an outgoing uses_map or starts edge, else "root_program";
       members = the component's nodes (sorted); node = members[0]; inferred true.
     A component that is a single program never counts as its own caller (ignore self edges).
  Entry point keys, in order:
    id "ep:<node id>", node, members, kind ("jcl_job"|"online"|"root_program"), name, inferred
    (false for jcl_job), confidence, trigger, steps, reach, touches, metrics, summary (null).
    trigger: jcl_job -> {type "batch", name = the job name, source_file, line = line_span[0]};
             online -> {type "user", name = the first transaction id started by any member (tx node
             name) or null, source_file, line}; root_program -> {type "none", name null, source_file, line}.
    reach: BFS over edges of kinds CODE starting from the members (all statuses of the targets are
      included, edges are followed from any node). Sorted ids, excluding the members themselves.
    touches: {reads, writes, screens, queues, external}: reads/writes = target ids of edges of kind
      reads/writes whose from is a member or in reach and whose context is null or in reach or the
      entry node; screens = targets of uses_map edges from those nodes; queues = the ids in reads/
      writes that start with "q:"; external = reach nodes with status system, gap or dynamic.
    metrics: {programs, copybooks, jobs_and_procs, lines (sum of card.lines), conditions (sum of
      card.conditions)}, counted over members + reach for nodes with those kinds.
    confidence: "low" if any reach node has status gap; else "medium" if any has status dynamic or if any
      reach edge has via "candidates"; else "high".
    steps (ordered):
      jcl_job: one item per step of the job IR in order: {order, name, node (step_targets), status
        (node status), exec_kind, parm, reads, writes, expands}. reads/writes = the dataset ids of the
        data edges whose context is this job and step equals this step name (access read -> reads,
        write -> writes, read_write -> both; unknown -> reads). For a step running a defined proc,
        expands = the proc's steps in the same shape (use context = the proc id and step name from the
        proc IR; depth limit 3; skip a proc already open). Otherwise expands [].
      online / root_program: BFS from the members along calls/links/xctl edges (depth limit 10, visited
        guard; neighbors ordered by the first ref line). Items {order, node, via ("start"|"calls"|
        "links"|"xctl"), from, line, maps, reads, writes} where maps/reads/writes come from that
        program's own uses_map/reads/writes edges (context null).
  find_cycles(unit_graph) / build_conversion_order(nodes, edges, entry_points) -> (cycles, order)
    Convertible nodes: status "defined", plus data nodes (kinds table, dataset, queue, cics_file) with
    any status. Not convertible (excluded[]): status system, gap, dynamic, and kinds transaction and
    unknown_target. ORDER = {copies, includes, calls, links, xctl, runs_program, runs_proc, uses_map,
    reads, writes} ("from needs to"); ignore "starts", self edges, and edges with a non-convertible end.
    Strongly connected components (iterative Tarjan, no recursion). Components of size > 1 are cycles:
    {id "cyc:<n>" (n from 1 in order of the smallest member id), members, via (sorted unique edge kinds
    inside it)}. Condense the graph; wave(unit) = 0 if it needs no other unit, else 1 + max(wave of the
    units it needs) (compute with a topological pass, no recursion). Units sorted by (wave, first member);
    ids "u:<n>" from 1 in that order. Unit: {id, kind ("single"|"cycle"), members, depends_on (unit ids,
    sorted), lines (sum of member card.lines), conditions, notes}. notes: "no source for data store"
    for a data node; "references gap <ids>" or "references dynamic <ids>" when a member has an edge to such
    nodes (first 5 ids).
    conversion_order = {basis: [the ORDER list], waves: [{wave, units: [unit...]}], excluded: [{node,
    status}], complete (true if no excluded gap/dynamic node is referenced by a convertible node),
    caveats: []}. Add the caveat "N references to missing source" and "N dynamic references" when > 0.

views.py
  fill_cards(nodes, edges, files, entry_points)  -> fills node.card by kind:
    program: {mode ("online" if it has uses_map/starts edges, "subprogram" if linkage.is_subprogram,
      else "batch"), lines, paragraphs, conditions, sql, cics, calls, params (linkage.params),
      callers (nodes with calls/links/xctl/runs_program edges to it), callees, copybooks (copies edge
      targets), stores_read, stores_written, screens, queues_named, private_queues, error_checks
      ({what: count} over all error_check events), header_comment, mode_hint null}
    copybook: {used_by, sections (unique), items (data item count), declares_table}
    jcl_job/jcl_proc: {steps (names in order), runs (target node ids), includes}
    bms_map: {mapset, maps, fields, used_by}
    table/dataset/queue/cics_file: {readers, writers, disp_seen (unique DISP strings of DDs that use
      the dataset, sorted), temporary, layout_copybook (tables only)}
    others: {}
    Also set on every node: used_by (entry point ids whose reach, members or touches contain it),
    fan_in and fan_out (distinct neighbor node counts over all edges).
  build_profile(nodes, files, entry_points) -> {files, by_type, total_lines (sum of header lines),
    programs, copybooks, jobs, procs, maps, tables, datasets, queues, entry_points,
    technology {jcl, cics, db2} (booleans), largest_programs (top 10 by lines {id, lines, paragraphs,
    conditions}), most_complex (top 10 by conditions)}
  build_data_view(nodes, edges) -> (data_stores, crud_matrix)
    data_stores: one per data node: {id, kind, name, status, defined_in, producers (nodes with writes
    edges), consumers (nodes with reads edges), layout: {program, record} from the first program whose
    files[] item (via its IR) has ddname matching a dd_join edge to this node and a non-null record, else
    null}. crud_matrix: {program id: {store id: "R"|"W"|"RW"}} for program nodes only, over every
    reads/writes edge to a data node.
  build_interfaces(nodes, edges, files) -> [{program, params, is_subprogram, callers: [{node, kind,
    file, line, args, commarea}]}] for defined programs with at least one caller (calls/links/xctl).
  build_screens(nodes, edges) -> [{id, mapset, maps, fields, used_by}] for bms_map nodes (all statuses).
  build_catalogs(files, entry_points) -> {messages: [{program, paragraph, line, text}] (every display
    event), job_steps: [{job, order, step, target, status, parm}] (every step of every job/proc IR),
    error_handling: [{program, counts}]}
  build_gaps(nodes, edges, entry_points, order) -> list: for every node with status "gap": {id, kind,
    name, referenced_by [{node, file, line}] (max 10), blocks_entry_points (entry points whose members
    or reach contain a referencing node), blocks_units (the units that contain a referencing node plus
    all units that depend on them directly or transitively)}.
  build_coupling(entry_points, nodes) -> list of pairs (a, b with a < b by id):
    {a, b, shared_code (ids of kinds program/jcl_proc/bms_map in both reach sets), shared_copybooks
    (copybooks in both reach sets), shared_reads, shared_writes, a_to_b (a.writes and b.reads),
    b_to_a, merge_candidate (true if shared_writes is non-empty)}. Only pairs where any list is non-empty.

quality.py
  build_quality(nodes, edges, files, dynamic_refs, order, extra_caveats) -> {counts: {files,
    by_type, nodes_by_kind, nodes_by_status, edges_by_status (counting aggregated edges)},
    resolved_ratio (edges with status resolved/system/external divided by all edges; 1.0 if no edges),
    unparsed_files (path, parse_status, first unparsed reason; for every file with parse_status
    "partial"), issues (all program.issues with the file path), dynamic_refs, caveats, authoritative}.
  authoritative = false if any gap node, any dynamic node, any dynamic_refs item, or any partial file.
  caveats (strings, only when the count > 0): "N files could not be fully parsed", "N references to
  missing source (gaps)", "N dynamic references", "N SQL/DDL files are not parsed" (files of type "sql"
  with no body), "No JCL found: dataset joins skipped" (no jcl IR at all and some program has files),
  "Duplicate ids: N" (duplicates), plus the info.caveats from build_edges.

builder.py
  build_project_ir(files, meta, progress=None, should_stop=None) -> dict | None
  Steps, calling progress("Project IR: <phase>") before each and checking should_stop() between them:
  nodes, edges, entry points, cards, cycles and order, data view, interfaces and catalogs, gaps and
  coupling, quality. If should_stop() is true return None (no file is written by the runner).
  Output dict keys, in order: schema_version "1.0", generated_at (UTC ISO), source_folder, ir_run
  (the ir_dir name), complete (meta complete), profile, nodes, edges, entry_points, cycles,
  conversion_order, data_stores, crud_matrix, interfaces, screens, catalogs, gaps, coupling,
  modules [], shared [], boundary_edges [], module_order [], duplicates, quality.

runner.py
  run_project_ir(ir_dir, output_root, progress=None, should_stop=None) -> dict
  loads the IR run, calls build_project_ir, writes <output_root>/<source-dir-name>_project_ir_
  <YYYYMMDD_HHMMSS>/project_ir.json (indent 2, ensure_ascii False, utf-8) and returns
  {"stopped": bool, "output_dir", "project_ir_path", "summary"} where summary = the profile plus
  {entry_points, waves, gaps, resolved_ratio, authoritative}. On stop return {"stopped": true}.
  output_root default: workspace/stage3_outputs.

app.py / index.html
  - Under the "Per-file IR" section add "Project IR" with a "Build project IR" button, enabled only
    when a completed IR run exists (the newest workspace/stage2_outputs/*_ir_*/ir_run.json whose
    "complete" is true, or the one just built). Same background mechanism, progress log, Stop button.
  - Result: the output folder, a "Download project_ir.json" link, then tables:
    * Profile counts (one line of "label: n" items).
    * Entry points: ID | Kind | Confidence | Steps | Reach | Reads | Writes (counts).
    * Conversion order: Wave | Units | Members (first 5 ids, then "+N").
    * Gaps: Name | Kind | Referenced by (first 3) | Blocks entry points (count).
    * Quality: resolved ratio, authoritative yes/no, and the caveats as a list.
    Rows/values with low confidence or gaps get style="background:#fff3cd".

TESTS  (tests/ir_fixtures.py builds hand-made per-file IR dicts; tests/test_project_ir.py)
  Fixtures (return (path, ir_dict) with every key the consolidator reads, defaults empty/null):
    prog(path, name, copybooks=[], sql=[], cics=[], calls=[], files=[], params=[], lines=100,
         conditions=0, events=[], subprogram=False)    # program IR
    job(path, name, steps=[])  with steps (stepname, "pgm"|"proc", target, [dds]) and dd
         (ddname, dsn, kind, access)
    cpy(path, name, declares_table=None, copies=[]) ; bms(path, mapset, maps=[])
  Items use the Part A shapes (sql item: {id, kind, tables, access, ...}; cics item with command,
  program, map, mapset, queue, dynamic, candidates, queue_scope, commarea, line, paragraph; calls
  item with target, dynamic, candidates, args, line).
  1. Statuses: program A copies ACCTREC (a cpy file exists), SQLCA, NOPE; calls B (exists) and ZZZ
     (missing); a dynamic call with no candidates; a dynamic call with candidates ["B"].
     Expect nodes: cpy:ACCTREC defined, cpy:SQLCA system, cpy:NOPE gap, pgm:B defined, pgm:ZZZ gap,
     dyn:A.<VAR> dynamic; edges with the right statuses; the candidate edge: to pgm:B, status
     "resolved", inferred true, via "candidates". quality.authoritative false.
  2. Data edges: P has sql select ACCOUNTS (line 10), update ACCOUNTS (line 20), insert into
     DB.TRANSACTIONS, and an OPEN of the same cursor. Expect tbl:ACCOUNTS and tbl:TRANSACTIONS
     (node qualified_names contains "DB.TRANSACTIONS"), kind table, status external; edge
     P->tbl:ACCOUNTS reads (count >= 1) and writes (count 1, refs line 20); no duplicate edges.
  3. DD join: job DAILY with step MAIN running P; dds INFILE (USER.IN, input, read), OUTFILE (USER.OUT,
     output, write), SYSOUT (null dsn, sysout); step PREP running IEFBR14 with a DD (USER.OLD, delete,
     write). P.files: INFILE (read), OUTFILE (write), UNUSED (read). Expect edges P->ds:USER.IN
     reads (context job:DAILY, step MAIN, via dd_join, inferred false) and P->ds:USER.OUT writes; no
     edge for SYSOUT; job:DAILY->ds:USER.OLD writes (inferred true, via disp, step PREP); the caveat
     "ddname UNUSED of ... has no DD in step MAIN of ..." exists. A program Q never run by any job with
     file ddname Z -> node dd:Z status "unmapped" and an edge.
  4. Entry points: job DAILY (steps MAIN then REPORT in order, with reads/writes per step); program R
     with no inbound edges -> root_program, inferred true; P (run by the job) is NOT a root; program S
     called by R is not a root; online program O with a uses_map edge and no inbound edges -> kind
     "online"; programs X and Y that xctl each other, both with uses_map -> ONE online entry point with
     two members. Check ids "ep:<node>", trigger types, steps order (R then S), reach, touches.
  5. Cycles and order: A calls B, B calls A, C calls A, A reads table T. Expect one cycle cyc:1 with
     members [pgm:A, pgm:B], via ["calls"]; waves: wave 0 = unit with tbl:T; wave 1 = the cycle unit
     (depends_on the T unit); wave 2 = unit with pgm:C. Gap and system nodes appear in excluded.
     Unit ids are u:1.. in (wave, member) order.
  6. Gap impact: A calls missing M; job J runs A. gaps has M with referenced_by [{node pgm:A, file,
     line}], blocks_entry_points containing ep:job:J, blocks_units containing the units of pgm:A and
     of job:J.
  7. Coupling: jobs J1 and J2 both write dataset X (via dd/disp edges) -> pair shared_writes [ds:X],
     merge_candidate true; J2 reads ds:Y that J1 writes -> a_to_b [ds:Y]; J1 and J3 share only a read of
     ds:Z -> shared_reads, merge_candidate false.
  8. Queues: program P1 writes literal queue 'MYQ', P2 reads it -> q:MYQ with writers/readers; a
     dynamic queue with scope session_private -> no node, card.private_queues 1, no dynamic_refs; scope
     unknown, no candidates -> dynamic_refs item with resolved false and no edge; scope shared with
     candidates ["Q1"] -> edge to q:Q1 via candidates and a dynamic_refs item resolved true.
  9. Online edges: a cics RETURN TRANSID('CC00') -> edge "starts" to tx:CC00 (status external),
     node tx:CC00 is in conversion_order.excluded; SEND MAP with mapset SGN00 where a bms file
     declares SGN00 -> uses_map edge to map:SGN00 status resolved; without the bms file -> gap node.
  10. Quality: edges with known statuses give the expected resolved_ratio; a partial file lists in
      unparsed_files; caveats contain the gap and dynamic sentences.
  11. End to end: write TESTPGM-like programs and a job in a tmp folder, run build_inventory, run_ir,
      then run_project_ir into a tmp dir: project_ir.json exists with all top-level keys listed above,
      modules == [] and the file loads.
  12. should_stop returning true before the entry point phase -> {"stopped": true}, no file written.

DO NOT
  - split into modules, call an LLM, add libraries, store source text, or change Stage 1.
  - add keys that are not listed, or classes (use functions and dicts).
  - use recursion for graph algorithms (use iterative versions).

HOW I WILL RUN IT (Windows PowerShell)
  python -m pytest
  python app.py   (run Stage 1, then Build IR, then Build project IR)
How to check it on the banking repo

Gaps should be ACCTREC, ERRHDLR and TRANREC (copybooks) and TRANPROC (program), with SQLCA marked system. quality.authoritative should be false.
Tables ACCOUNTS and TRANSACTIONS should be in wave 0 of the order.
DAILY and EOD should show up as coupled in coupling, through USER.TRANOUT, USER.RECONCIL and USER.INTRPT. This is the case where merge_candidate should be true.
The blocks_entry_points for TRANPROC should list the DAILY job.
Check CUPO003 first on your Danish folder after re-running Build IR: the LINK entries that had a null program should now have a target, or an item in program.issues with the first 80 characters of the statement. Send me any issues entries and I'll tell you the pattern to fix.

Files hidden when shared

Created a file, ran a command, shared files
Created a file, ran a command, shared files
I can't verify the Stage 3 code from this report, because I haven't seen it. A passing suite of 80 tests also doesn't show the output matches the spec. So I wrote check_project_ir.py, which checks a real project_ir.json against the rules in the prompt. Run it on the banking repo output:

python check_project_ir.py workspace\stage3_outputs\<folder>\project_ir.json
It checks:

top-level key order, and that the empty module fields really are empty
node and edge key order and statuses, that every edge endpoint is a real node, and that edges are properly aggregated (no duplicates, at most 10 refs)
entry point shape, and that the job entry points match the job nodes
the conversion-order rules: wave numbers follow the dependency rule, unit ids run u:1..n, cycles are single units, and no defined node is excluded
the gaps list against the gap nodes, the resolved ratio recomputed from the edges, and the coupling pairs
It prints FAIL: lines for violations, then a short summary to read by eye. I tested it only on a tiny hand-made file, not on your output.

Things in Copilot's report I'd check

The page section is not mentioned. My prompt asked for a "Build project IR" button and result tables (profile, entry points, order, gaps, quality). The report says only that the page and routes were kept. Please check whether the page has that section.
API endpoints were added that I didn't ask for. They're harmless, but check that the page still works through the same code.
Stage 1 still lists "gaps, entry points" in the inventory result. That's fine, but the project IR is now the authoritative source for both, so they shouldn't be shown as competing answers.
Facts I expect on the banking repo

Gaps: cpy:ACCTREC, cpy:ERRHDLR, cpy:TRANREC and pgm:TRANPROC, with cpy:SQLCA as system.
tbl:ACCOUNTS and tbl:TRANSACTIONS in wave 0.
DAILY and EOD marked as a merge_candidate pair through USER.TRANOUT.
Please send me the script's output and the entry_points and gaps sections of your two runs (banking and CUPO003). The null LINK targets from earlier are the first thing I'll look for.

Check project ir
PY
