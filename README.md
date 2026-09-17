# Claude Code Prompting

How to write prompts for Claude Code that get correct results, why the structure works, and how it connects to retrieval-augmented generation.

The examples use a small Python calculator (in `example/`) that you can clone and try.

## The prompt structure

Every prompt has four parts:

1. **Task.** One sentence.
2. **Context.** Where things live and what pattern to follow.
3. **Requirements.** Explicit, testable constraints, including what not to touch.
4. **Done-when.** A command the model can run to check its own work, plus what to do after.

### Template

```
<One-sentence task.>

Context:
- <Where the relevant code lives.>
- <The pattern or convention to follow.>
- <Where tests live and how to run them.>

Requirements:
- <Specific thing to add or change.>
- <Specific constraint.>
- Do not change <things that must stay untouched>.

Done when: `<verification command>` passes. Run it and show me the output.
Then <what to do after: commit, open a PR, summarize, etc.>.
```

### Example 1: add a feature

```
Add a multiply operation to calc.py.

Context:
- OPS in calc.py maps a command name to a function; follow that pattern.
- Tests live in test_calc.py and use pytest.

Requirements:
- Add multiply(a, b) and register it in OPS under "mul".
- Add test_multiply to test_calc.py.
- Do not change add or subtract.

Done when: `pytest -q` passes. Run it and show me the output.
Then commit with the message "Add multiply".
```

### Example 2: add a feature with an error case

```
Add a divide operation to calc.py.

Context:
- OPS in calc.py maps a command name to a function; follow that pattern.
- Tests live in test_calc.py and use pytest.

Requirements:
- Add divide(a, b) and register it in OPS under "div".
- Dividing by zero must raise ValueError with the message "cannot divide by zero".
- Add test_divide and test_divide_by_zero to test_calc.py.
- Do not change add or subtract.

Done when: `pytest -q` passes. Run it and show me the output.
Then commit with the message "Add divide".
```

### Example 3: resolve a merge conflict

```
There is a merge conflict in calc.py and test_calc.py from merging the divide branch.
Both sides added a new operation. Keep both operations and both sets of tests.
Resolve the conflicts, run `pytest -q`, show me the output, then finish the merge commit.
```

## Why this structure works

A language model does not know your codebase. It generates the most probable continuation given whatever is in its context window. If the prompt is "add multiply," the model has to guess the file, the naming convention, whether tests exist, and what finished looks like. Every guess is drawn from its training-data priors, which are averaged over millions of other repos, not yours. Vague prompt, wide distribution of possible outputs, higher chance of one you did not want.

Each part of the prompt narrows that distribution:

- **Context** replaces guesses with facts. Naming `OPS` and `test_calc.py` means the model reads those instead of searching or inventing.
- **Requirements** turn a fuzzy goal into checkable constraints. "Do not change add or subtract" removes a whole class of unwanted edits.
- **Done-when** gives the model a feedback signal. Claude Code is agentic: it runs commands, reads the output, and adjusts. A failing test is far more informative than a human saying "that looks wrong." Without a check, the model stops when the output looks plausible; with one, it stops when the output is correct.

Short version: the prompt is not instructions for a person, it is the conditioning input for a probability distribution. The more relevant, specific information you put in, the tighter that distribution gets around the answer you want.

### "But doesn't Claude Code learn my codebase?"

No, and the distinction is the whole point. There are three layers:

1. **Weights.** What the model learned in training. General programming knowledge, nothing about your repo. Never change during use.
2. **Persistent context.** `CLAUDE.md`, memory files, settings. Read into the context window at the start of every session, automatically. This is what feels like "learning," and it is just curated retrieval you set up once.
3. **Per-turn context.** Your prompt plus whatever Claude greps and reads while working. Gone when the session ends.

`CLAUDE.md` is the Context section of your prompt, made permanent. When `/init` writes one, Claude is doing the retrieval step once and saving the result to disk so it does not have to redo it every session. Auto-memory works the same way: notes written to files, read back in later. Nothing about the model itself changes.

What would change the weights: fine-tuning. Claude Code does not do that.

## RAG, part 1: the concept

A language model has exactly two sources of information when you send it a request: its weights, fixed when training ended, and its context window, whatever text is in front of it right now. Your codebase is not in the weights. Your docs, tickets, and conventions are not in there. If you want the model to work with your material, it has to go in the context window.

That is the problem Retrieval-Augmented Generation solves. Before the model generates anything, fetch the relevant material and put it in the prompt.

### The classic pipeline

1. **Chunk.** Split the corpus into pieces small enough that several fit in a prompt.
2. **Embed.** Run each chunk through an embedding model that turns text into a vector. Text with similar meaning ends up close together in that vector space.
3. **Index.** Store the vectors, usually in a vector database.
4. **Retrieve.** At query time, embed the question the same way, find the nearest chunks, optionally rerank them with a second model.
5. **Generate.** Paste the top chunks into the prompt next to the question. The model answers from those.

The model never sees the whole corpus. It sees the handful of chunks the retriever picked. Everything depends on that pick.

### Where it breaks

Every way RAG fails is a retrieval failure, not a generation failure:

- The retriever grabs the wrong chunks because the question used different words than the answer. The model answers confidently from the wrong material.
- It grabs the right chunk, but the chunk boundary cut off what made it make sense. The function signature is in chunk twelve, the body in chunk thirteen, you only got twelve.
- The corpus changed and the index did not. The model builds on stale code.
- Too much was retrieved. Forty chunks in the window, and the model pays less attention to what is buried in the middle.

In every case the generation step is doing its job: producing a plausible answer from what it was given. The problem is what it was given. **The generation step cannot fix a bad retrieval step.** Output quality is bounded by what got into context.

## RAG, part 2: how Claude Code does it

Claude Code does not build an embedding index of your repo. There is no vector database. It does retrieval agentically: the model decides what to look for, runs a tool, reads what came back, and decides if it needs more. Same principle, different mechanism.

### The tools

- **Glob.** Find files by name or pattern. "Where are the tests" becomes a search for `test_*.py`.
- **Grep.** Search file contents. "Where is OPS defined" becomes a regex across the repo.
- **Read.** Pull a file or a range of lines into context.
- **Bash.** `git log`, `git diff`, running the test suite. Command output is retrieved context too.

This is keyword and structure search, not semantic search, and it fits code well. Code has exact identifiers, exact paths, a directory tree. Embedding search is better for "find the paragraph about this idea." Grep is better for "find every place this symbol is used." For a codebase, you want the second one most of the time.

### Iterative, not one-shot

Classic RAG retrieves once, up front. Claude Code retrieves in a loop: search, read, realize it also needs the caller, search again, read that. It refines its own query based on what it found.

This is why the prompt structure matters. The prompt is the starting point of the search. If the starting point is vague, the model wanders around the repo before it lands on the right files, or never lands and guesses.

### Layers of context, in the order they arrive

1. **CLAUDE.md.** Loaded automatically at session start. Context you retrieved once, by hand, and saved. Claude reads it from the repo root and from subdirectories as it works in them, so project-wide facts go at the root and module-specific facts go next to the code.
2. **Your prompt.** The question plus whatever you hand-feed it. "OPS in calc.py maps a command name to a function" is you doing the first retrieval step yourself.
3. **Tool results.** Everything grep, read, and command output bring back during the task. In a real session this is most of the context.
4. **Memory.** Claude Code can write notes to itself that persist across sessions. Same mechanism as CLAUDE.md, files on disk read back in, written by the model instead of you.

### Managing the window

The window is finite and agentic retrieval fills it fast.

- **Compaction.** When the window fills, the conversation is summarized and the summary replaces the transcript. Old tool results get compressed. Anything that only existed in an old grep result may need to be retrieved again.
- **Subagents.** When a task needs a lot of reading, Claude can spin up a subagent with its own fresh window, let it do the digging, and get back just the conclusion. The parent window stays clean.

### What you control

- **Steer the retrieval.** Name the files, functions, patterns, and conventions in your prompt. Put durable facts in `CLAUDE.md` so they are retrieved for free every session. Every fact you supply is a search Claude does not have to run and a guess it does not have to make.
- **Keep the corpus clean.** Whatever is on disk is what gets retrieved. A checkout with three unrelated half-finished changes means every grep and every read picks up all three, and the model builds on whichever it happened to see. Git worktrees (`claude --worktree <name>`) give each session its own branch and directory, so what it retrieves is exactly what its task needs. Worktrees are retrieval hygiene.

## Try it

```
cd example
pip install pytest
pytest -q
claude
```

Then paste Example 1.
