import tkinter as tk
from abc import abstractmethod

import ttkbootstrap as tb

from chemcards.database.core import MoleculeDB
from chemcards.flashcards.core import (
    FlashCardGeneratorBase,
)
from chemcards.flashcards.filters import MissingTargetFilter
from chemcards.flashcards.multiplechoice import (
    MultipleChoiceGeneratorBase,
    MultipleChoiceMoleculeToTargetGenerator,
    MultipleChoiceMoleculeToNameGenerator,
    MultipleChoiceNameToMoleculeGenerator,
    MultipleChoiceMoleculeToFunctionalGroupNameGenerator

)
from chemcards.gui.core import WindowOptions, FontDefaults
from chemcards.gui.molecules import MoleculeViz, MoleculeWindow


class MultipleChoiceQuizBase:
    name = "Quiz Base"

    def __init__(self, main_window: "MainWindow"):
        self.option_selected = tk.IntVar()
        self.correct = 0
        self.total_number_of_questions = 0
        self.main_window = main_window
        self.gui = main_window.gui
        self.window_options = WindowOptions()

        self.frame = tb.Frame(
            self.gui,
            height=self.window_options.frame_height,
            width=self.window_options.frame_width,
            bootstyle="dark",
        )
        self.frame.pack(
            padx=self.window_options.frame_padding / 2, pady=self.window_options.frame_padding / 2
        )

        self.molecule_database: MoleculeDB = MoleculeDB.load()

        self.question_generator: MultipleChoiceGeneratorBase = (
            self.get_question_generator()
        )

        self.make_frames()

    @abstractmethod
    def make_frames(self):
        pass

    @abstractmethod
    def get_question_generator(self) -> MultipleChoiceGeneratorBase:
        pass

    def add_check_answer_button(self):
        # Check Answer
        check_answer_button = tb.Button(
            self.control_frame,
            text="Check My Answer",
            command=self.check_answer,
        )
        check_answer_button.grid(row=1, column=0, padx=self.window_options.between)

    def check_answer(self):
        option_selected = self.option_selected.get()
        self.option_buttons[option_selected].configure(
            bootstyle="danger.Outline.Toolbutton"
        )
        self.option_buttons[self.current_question.answer_index].configure(
            bootstyle="success.Outline.Toolbutton"
        )
        self.total_number_of_questions += 1
        if option_selected == self.current_question.answer:
            self.correct += 1

    def add_next_button(self):
        next_button = tb.Button(
            self.control_frame,
            text="Next",
            command=self.next_question,
        )
        next_button.grid(row=1, column=1, padx=self.window_options.between)

    def add_end_button(self):
        end_button = tb.Button(
            self.control_frame,
            text="Finish Quiz",
            command=self.end,
        )
        end_button.grid(row=1, column=2, padx=self.window_options.between)

    def make_molecule_window(self):
        # Show the answer_molecule if present, otherwise show the display (which may be a FunctionalGroup)
        target = None
        if getattr(self, 'current_question', None):
            if self.current_question.answer_molecule:
                target = self.current_question.answer_molecule
            elif self.current_question.display:
                target = self.current_question.display
        if target is not None:
            # If the target is a FunctionalGroup, open the FunctionalGroupWindow
            from chemcards.database.cheminformatics import FunctionalGroup
            from chemcards.gui.molecules import FunctionalGroupWindow
            if isinstance(target, FunctionalGroup):
                FunctionalGroupWindow(target, self.gui)
            else:
                MoleculeWindow(target, self.gui)

    def add_molecule_info_button(self):
        molecule_info_button = tb.Button(
            self.control_frame,
            text="View Molecule Info",
            command=self.make_molecule_window,
        )
        molecule_info_button.grid(row=1, column=3, padx=self.window_options.between)

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
        self.add_molecule_info_button()

    def next_question(self):
        self.current_question = self.question_generator.next()
        self.display_question()

    def destroy_buttons(self):
        for widget in self.frame.winfo_children():
            widget.destroy()

    def start(self):
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


class MultipleChoiceTextToImageQuizBase(MultipleChoiceQuizBase):
    name = "Multiple Choice (Text to Image) Quiz Base"

    def make_frames(self):
        self.title_frame = tb.Frame(self.frame)
        self.title_frame.grid(row=0, pady=self.window_options.between)

        self.question_frame = tb.Frame(self.frame)
        self.question_frame.grid(row=1, pady=self.window_options.between)

        self.display_frame = tb.Frame(self.frame)
        self.display_frame.grid(row=2, pady=self.window_options.between)
        # self.display_frame.grid(row=2, column=0, columnspan=4)

        self.control_frame = tb.Frame(self.frame)
        self.control_frame.grid(row=3, pady=self.window_options.between)

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

        # # Display
        # self.display_panel = tb.Label(self.display_frame)
        # self.display_panel.pack(anchor="e")

        # Options
        # initialize the list with an empty list of options
        button_list = []

        self.option_selected.set(0)

        # adding the options to the list
        for i in range(4):
            # setting the radio button properties
            radio_btn = tb.Radiobutton(
                self.display_frame,
                variable=self.option_selected,
                value=i,
                bootstyle="info.Outline.Toolbutton",
            )

            # adding the button to the list
            button_list.append(radio_btn)

            # placing the button
            radio_btn.grid(row=0, column=i, padx=self.window_options.between)

        # return the radio buttons
        self.option_buttons = button_list

    def display_question(self):

        # setting the Question properties
        self.question_label.configure(text=self.current_question.question)

        self.option_selected.set(0)
        for i, choice in enumerate(self.current_question.choices):
            mviz = MoleculeViz(choice)
            img = mviz.get_image(250, 250)

            # I don't understand why but both of these lines are neccessary
            self.option_buttons[i].image = img
            self.option_buttons[i].configure(
                # text=choice,
                bootstyle="info.Outline.Toolbutton",
                image=img,
            )


class MultipleChoiceImageToTextQuizBase(MultipleChoiceQuizBase):
    name = "Multiple Choice (Image to Text) Quiz Base"

    def make_frames(self):
        self.title_frame = tb.Frame(self.frame)
        self.title_frame.grid(row=0, pady=self.window_options.between)

        self.question_frame = tb.Frame(self.frame)

        # Anchor the question frame to the left of its column
        self.question_frame.grid(row=1, column=0, pady=self.window_options.between, padx=self.window_options.between, sticky='w')

        self.display_frame = tb.Frame(self.frame)
        # Keep the display frame to the right of the question frame and anchor it to the left so it sits adjacent
        self.display_frame.grid(row=1, column=1, pady=self.window_options.between, padx=self.window_options.between, sticky='w')

        # Prevent the frame columns from expanding and pushing the display to the far right
        try:
            # grid_columnconfigure may not be necessary in all tk wrappers, but it's safe to call
            self.frame.grid_columnconfigure(0, weight=0)
            self.frame.grid_columnconfigure(1, weight=0)
        except Exception:
            pass

        self.control_frame = tb.Frame(self.frame)
        self.control_frame.grid(row=2, columnspan=2, pady=self.window_options.between)

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
        # Center the display image within its frame so it appears right next to the options
        self.display_panel.pack(anchor="center", padx=self.window_options.between, pady=self.window_options.between)

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
            radio_btn.pack(pady=self.window_options.between)

        # return the radio buttons
        self.option_buttons = button_list

    def display_question(self):

        # setting the Question properties
        self.question_label.configure(text=self.current_question.question)

        if self.current_question.display:

            img = MoleculeViz(self.current_question.display).get_image()

            # I don't understand why but both of these lines are neccessary
            self.display_panel.image = img
            self.display_panel.configure(image=img)

        self.option_selected.set(0)
        for i, choice in enumerate(self.current_question.choices):
            self.option_buttons[i].configure(
                text=choice, bootstyle="info.Outline.Toolbutton"
            )


class MultipleChoiceMoleculeToTargetQuiz(MultipleChoiceImageToTextQuizBase):
    name = MultipleChoiceMoleculeToTargetGenerator.name

    def get_question_generator(self) -> FlashCardGeneratorBase:
        return MultipleChoiceMoleculeToTargetGenerator(self.molecule_database)


class MultipleChoiceMoleculeToNameQuiz(MultipleChoiceImageToTextQuizBase):
    name = MultipleChoiceMoleculeToNameGenerator.name

    def get_question_generator(self) -> FlashCardGeneratorBase:
        return MultipleChoiceMoleculeToNameGenerator(self.molecule_database)


class MultipleChoiceNameToMoleculeQuiz(MultipleChoiceTextToImageQuizBase):
    name = MultipleChoiceNameToMoleculeGenerator.name

    def get_question_generator(self) -> FlashCardGeneratorBase:
        return MultipleChoiceNameToMoleculeGenerator(self.molecule_database)

class MultipleChoiceMoleculeToFunctionalGroupNameQuiz(MultipleChoiceImageToTextQuizBase):
    name = MultipleChoiceMoleculeToFunctionalGroupNameGenerator.name

    def get_question_generator(self) -> FlashCardGeneratorBase:
        return MultipleChoiceMoleculeToFunctionalGroupNameGenerator(self.molecule_database)