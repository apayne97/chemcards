import tkinter as tk
from abc import abstractmethod

import ttkbootstrap as tb

from chemcards.database.core import MoleculeDB
from chemcards.flashcards.core import FlashCardGeneratorBase
from chemcards.flashcards.filters import MissingTargetFilter
from chemcards.flashcards.multiplechoice import MultipleChoiceGenerator
from chemcards.gui.core import PaddingAndSize, FontDefaults
from chemcards.gui.molecules import MoleculeViz


class QuizBase:
    name = "Quiz Base"

    def __init__(self, main_window: "MainWindow"):
        self.option_selected = tk.IntVar()
        self.correct = 0
        self.total_number_of_questions = 0
        self.main_window = main_window
        self.gui = main_window.gui

        self.frame = tb.Frame(
            self.gui,
            height=PaddingAndSize.frame_height,
            width=PaddingAndSize.frame_width,
            bootstyle="dark",
        )
        self.frame.pack(
            padx=PaddingAndSize.frame_padding / 2, pady=PaddingAndSize.frame_padding / 2
        )
        self.make_frames()

    @abstractmethod
    def make_frames(self):
        pass

    @abstractmethod
    def load_molecule_database(self):
        self.question_generator: FlashCardGeneratorBase
        pass

    @abstractmethod
    def add_check_answer_button(self):
        pass

    @abstractmethod
    def check_answer(self):
        pass

    @abstractmethod
    def add_next_button(self):
        pass

    @abstractmethod
    def add_end_button(self):
        pass

    @abstractmethod
    def display_question(self):
        pass

    @abstractmethod
    def _make_buttons(self):

        pass

    def make_buttons(self):
        self._make_buttons()
        self.add_check_answer_button()
        self.add_next_button()
        self.add_end_button()

    def next_question(self):
        self.current_question = self.question_generator.next()
        self.display_question()

    def destroy_buttons(self):
        for widget in self.frame.winfo_children():
            widget.destroy()

    def start(self):
        self.load_molecule_database()
        self.make_buttons()
        self.next_question()

    def end(self):
        self.destroy_buttons()
        report = tb.Label(
            self.frame,
            text=f"Congrats! You answsered {self.total_number_of_questions} questions, and got {self.correct} of them correct!",
            font=FontDefaults.subtitle(),
        )
        report.pack()

        back_to_main_menu = tb.Button(
            self.frame,
            text="Return to Main Menu",
            command=self.main_window.start,
        )
        back_to_main_menu.pack()


class MultipleChoiceQuiz(QuizBase):
    name = "Multiple Choice Quiz"

    def make_frames(self):
        self.title_frame = tb.Frame(self.frame)
        self.title_frame.pack(side="top", pady=PaddingAndSize.between)

        self.question_frame = tb.Frame(self.frame)
        self.question_frame.pack(
            side="left", padx=PaddingAndSize.between, pady=PaddingAndSize.between
        )

        self.display_frame = tb.Frame(self.frame)
        self.display_frame.pack(
            side="right", pady=PaddingAndSize.between, padx=PaddingAndSize.between
        )

    def load_molecule_database(self):
        mdb = MoleculeDB.load()
        self.question_generator = MultipleChoiceGenerator(
            mdb, filters=[MissingTargetFilter()]
        )

    def add_check_answer_button(self):
        # Check Answer
        check_answer_button = tb.Button(
            self.display_frame, text="Check My Answer", command=self.check_answer
        )
        check_answer_button.pack(pady=PaddingAndSize.between)

    def add_next_button(self):
        next_button = tb.Button(
            self.display_frame,
            text="Next",
            command=self.next_question,
        )
        next_button.pack(pady=PaddingAndSize.between)

    def add_end_button(self):
        end_button = tb.Button(
            self.display_frame,
            text="Finish Quiz",
            command=self.end,
        )
        end_button.pack(pady=PaddingAndSize.between)

    def _make_buttons(self):
        # Title
        self.question_label = tb.Label(
            self.title_frame,
            text="",
            font=FontDefaults.title(),
            bootstyle="primary",
        )
        # placing the option on the screen
        self.question_label.pack(anchor="w", side="top")

        # Display
        self.display_panel = tb.Label(self.display_frame)
        self.display_panel.pack(anchor="e")

        # Options
        # initialize the list with an empty list of options
        button_list = []

        self.option_selected.set(0)

        # adding the options to the list
        for i in range(4):
            # setting the radio button properties
            radio_btn = tb.Radiobutton(
                self.question_frame,
                text="",
                variable=self.option_selected,
                # width=100,
                value=i,
                bootstyle="info.Outline.Toolbutton",
            )

            # adding the button to the list
            button_list.append(radio_btn)

            # placing the button
            radio_btn.pack(pady=PaddingAndSize.between)

        # return the radio buttons
        self.option_buttons = button_list

    def display_question(self):

        # setting the Question properties
        self.question_label.configure(text=self.current_question.question)

        if self.current_question.display:

            from PIL import ImageTk, Image

            mviz = MoleculeViz(self.current_question.display)
            filename = mviz.get_image()
            img = Image.open(filename)
            img = img.resize((250, 250))
            img = ImageTk.PhotoImage(img)
            self.display_panel.image = img
            self.display_panel.configure(image=img)

        self.option_selected.set(0)
        for i, choice in enumerate(self.current_question.choices):
            self.option_buttons[i].configure(
                text=choice, bootstyle="info.Outline.Toolbutton"
            )

    def check_answer(self):
        option_selected = self.option_selected.get()
        self.option_buttons[option_selected].configure(
            bootstyle="danger.Outline.Toolbutton"
        )
        self.option_buttons[self.current_question.answer].configure(
            bootstyle="success.Outline.Toolbutton"
        )
        self.total_number_of_questions += 1
        if option_selected == self.current_question.answer:
            self.correct += 1
