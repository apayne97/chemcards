My goal is basically to make fancy flashcards for
1. chemical functional groups relevant to drug discovery
2. stories of real drugs so that I don't look like an idiot without a knowledge of the history of drug discovery

I think it would be neat to automatically download, i.e. [drugbank](https://go.drugbank.com/) entries and process them and incorporate them into a flashcard like system

It would be nice to organize / categorize the questions so that you could focus on:
- just kinase drugs
- just membrane protein drugs
- just drugs with certain functional groups (triazole, etc)

At a minimum the "game" could be played in a terminal, but even better would be able to host a local web page that would have different kinds of quiz questions, etc

# Types of questions:
Multiple choice:
- pick the functional group these drugs have in common (easy - structures of drugs, hard - name of class of drugs)
- pick the target of a drug, drug for target
- functional group to name

Fill in the blank (I think this might suck without some kind of text-processing, otherwise exact text matches will be frustrating)
- oh an idea for this would be to be able to show the answer + your guess after the question and ask you "add this answer to the database?" if you think your answer was a correct version of the right answer

The most difficult version would be to have the Mastering chemistry-esque "draw in the functional group" type of question


# Features
- memory of what questions have been asked with your guesses + answers; maybe even a report of what kinds of questions you got right / wrong etc

# To Do
- [x] import from chembl
- [x] save json files of imported data
- [x] use rdkit for processing molecules
- [x] use importlib resources to load those in
- [x] construct a generator using some filtering logic
- [x] use tkinter to interact with the questions
- [x] use `generators` to create questions from the possible choices


# Design Ideas
- import from Drug Bank, etc
  - Drug Bank
  - pubchem
- save question + possible answers + chosen answer + correct answer into i.e. a CSV
- add GUI molecule drawing interface from, i.e. https://github.com/nicemicro/nicemolecules/tree/main