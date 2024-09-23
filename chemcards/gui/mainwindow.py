import tkinter as tk

import ttkbootstrap as tb

from chemcards.gui.core import PaddingAndSize, FontDefaults
from chemcards.gui.quizwindow import QuizBase, MultipleChoiceMoleculeToTargetQuiz, MultipleChoiceMoleculeToNameQuiz

# QUIZZES = [MultipleChoiceMoleculeToTargetQuiz, MultipleChoiceMoleculeToNameQuiz]

QUIZZES = {quiz.name: quiz for quiz in [MultipleChoiceMoleculeToTargetQuiz, MultipleChoiceMoleculeToNameQuiz]}


class MainWindow:
    def __init__(self):
        self.gui = tb.Window(themename="superhero")
        self.gui.title("ChemCards")
        self.gui.geometry(PaddingAndSize.window_size)
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
            padx=PaddingAndSize.edge,
            pady=PaddingAndSize.edge,
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
            quiz_button = tb.Button(
                text=name,
                command=lambda: self.start_quiz(name),
                bootstyle="primary.TButton",
            )
            quiz_button.pack(pady=PaddingAndSize.between)
            self.quiz_buttons.append(quiz_button)

    def start(self):

        for widget in self.gui.winfo_children():
            widget.destroy()

        self.make_buttons()

        self.title_label = tb.Label(
            text="Welcome to ChemCards",
            font=FontDefaults.title(),
        )
        self.title_label.pack(pady=PaddingAndSize.edge)

        self.subtitle_label = tb.Label(
            text="Choose a quiz to start", font=FontDefaults.subtitle()
        )
        self.subtitle_label.pack(pady=PaddingAndSize.between)

        self.add_quiz_buttons()

        self.all_buttons.extend(
            [self.title_label, self.subtitle_label, *self.quiz_buttons]
        )

        self.gui.mainloop()
