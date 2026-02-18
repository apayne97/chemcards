import tkinter as tk

import ttkbootstrap as tb

from chemcards.gui.core import WindowOptions, FontDefaults
from chemcards.gui.quizwindow import (
    MultipleChoiceMoleculeToTargetQuiz,
    MultipleChoiceMoleculeToNameQuiz,
    MultipleChoiceNameToMoleculeQuiz,
    MultipleChoiceMoleculeToFunctionalGroupNameQuiz,
)
from functools import partial

QUIZZES = {
    quiz.name: quiz
    for quiz in [
        MultipleChoiceMoleculeToTargetQuiz,
        MultipleChoiceMoleculeToNameQuiz,
        MultipleChoiceNameToMoleculeQuiz,
        MultipleChoiceMoleculeToFunctionalGroupNameQuiz,
    ]
}


class MainWindow:
    def __init__(self):
        self.window_options = WindowOptions.from_screen()
        self.gui = tb.Window(themename="superhero")
        self.gui.title("ChemCards")
        self.gui.geometry(self.window_options.window_size)
        self.quiz_buttons = []
        self.all_buttons = []

        self.my_style = tb.Style()
        self.my_style.configure("info.Outline.Toolbutton", font=FontDefaults.text())
        self.my_style.configure("success.Outline.Toolbutton", font=FontDefaults.text())
        self.my_style.configure("danger.Outline.Toolbutton", font=FontDefaults.text())
        self.my_style.configure("danger.Toolbutton", font=FontDefaults.text())
        self.my_style.configure("light.Toolbutton", font=FontDefaults.text())
        self.my_style.configure("primary.TButton", font=FontDefaults.text())
        self.my_style.configure("danger.TButton", font=FontDefaults.text())

    def destroy(self):
        self.gui.destroy()

    def make_buttons(self):
        self.quit_button = tb.Button(
            text="Quit",
            command=self.destroy,
            bootstyle="danger.TButton",
        )

        # placing the Quit button on the screen
        self.quit_button.pack(
            side=tk.RIGHT,
            anchor=tk.NE,
            padx=self.window_options.edge,
            pady=self.window_options.edge,
        )

    def destroy_buttons(self):
        for button in self.all_buttons:
            button.destroy()

    def start_quiz(self, quiz_name: str):
        self.destroy_buttons()
        quiz = QUIZZES[quiz_name](self)
        quiz.start()

    def add_quiz_buttons(self):
        for name in QUIZZES.keys():
            partial_func = partial(self.start_quiz, name)
            quiz_button = tb.Button(
                text=name,
                command=partial_func,
                bootstyle="primary.TButton",
            )
            quiz_button.pack(pady=self.window_options.between)
            self.quiz_buttons.append(quiz_button)

    def start(self):

        for widget in self.gui.winfo_children():
            widget.destroy()

        self.make_buttons()

        self.title_label = tb.Label(
            text="Welcome to ChemCards",
            font=FontDefaults.title(),
        )
        self.title_label.pack(pady=self.window_options.edge)

        self.subtitle_label = tb.Label(
            text="Choose a quiz to start", font=FontDefaults.subtitle()
        )
        self.subtitle_label.pack(pady=self.window_options.between)

        self.add_quiz_buttons()

        self.all_buttons.extend(
            [self.title_label, self.subtitle_label, *self.quiz_buttons]
        )

        self.gui.mainloop()
