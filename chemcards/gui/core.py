import tkinter as tk
import ttkbootstrap as tb
from pydantic import BaseModel, Field
from chemcards.flashcards.core import MultipleChoice
from chemcards.database.core import MoleculeDB
import random
from chemcards.gui.molecules import MoleculeViz


class QuizBase:
    name = "Quiz Base"

    def __init__(self):
        self.option_selected = tk.IntVar()
        self.correct = 0
        self.total_number_of_questions = 0


class MultipleChoiceQuiz(QuizBase):
    name = "Multiple Choice Quiz"

    def __init__(self, gui):
        super().__init__()
        self.gui = gui
        self.frame = tk.Frame(self.gui, width=600, height=600)
        self.frame.pack()
        self.mdb = MoleculeDB.load().filter_missing_target()
        self.display_panel = tk.Label(self.frame)
        self.current_question: MultipleChoice = None
        self.option_buttons = []
        self.question_label = tk.Label(self.frame)

    def start(self):

        self.next_question()

        next_button = tk.Button(
            self.frame,
            text="Next",
            command=self.next_question,
            width=10,
            bg="blue",
            fg="white",
            font=("ariel", 16, "bold"),
        )

        # placing the button  on the screen
        next_button.place(x=450, y=380)

        end_button = tk.Button(
            self.frame,
            text="Finish Quiz",
            command=self.end,
            width=10,
            bg="red",
            fg="white",
            font=("ariel", 16, "bold"),
        )
        end_button.place(x=450, y=450)

    def destroy_buttons(self):
        for widget in self.frame.winfo_children():
            widget.destroy()

    def end(self):
        self.destroy_buttons()
        report = tk.Label(
            self.frame,
            text=f"Congrats! You answsered {self.total_number_of_questions} questions, and got {self.correct} of them correct!",
            width=100,
            bg="black",
            fg="white",
            font=("ariel", 24, "bold"),
        )
        report.place(x=100, y=100)

        back_to_main_menu = tk.Button(
            self.frame,
            text="Return to Main Menu",
            command=self.gui.start,
            width=20,
            bg="red",
            fg="white",
            font=("ariel", 16, "bold"),
        )
        back_to_main_menu.place(x=350, y=350)

    def display_options(self):

        # initialize the list with an empty list of options
        button_list = []

        # position of the first option
        y_pos = 250

        self.option_selected.set(0)

        # adding the options to the list
        for i, choice in enumerate(self.current_question.choices):
            # setting the radio button properties
            radio_btn = tk.Radiobutton(
                self.frame,
                text=choice,
                variable=self.option_selected,
                value=i,
                font=("ariel", 14),
            )

            # adding the button to the list
            button_list.append(radio_btn)

            # placing the button
            radio_btn.place(x=100, y=y_pos)

            # incrementing the y-axis position by 40
            y_pos += 40

        # return the radio buttons
        self.option_buttons = button_list

    def display_question(self):

        # setting the Question properties
        self.question_label = tk.Label(
            self.frame,
            text=self.current_question.question,
            width=60,
            font=("ariel", 16, "bold"),
            anchor="w",
        )

        # placing the option on the screen
        self.question_label.place(x=70, y=100)

        if self.current_question.display is not None:
            from PIL import ImageTk, Image

            mviz = MoleculeViz(self.current_question.display)
            filename = mviz.get_image()
            img = Image.open(filename)
            img = img.resize((250, 250))
            img = ImageTk.PhotoImage(img)
            self.display_panel = tk.Label(self.frame, image=img)
            self.display_panel.image = img
            self.display_panel.place(x=350, y=0)

    def check_answer(self):
        option_selected = self.option_selected.get()
        self.option_buttons[option_selected]["background"] = "red"
        self.option_buttons[self.current_question.answer]["background"] = "green"
        self.total_number_of_questions += 1
        if option_selected == self.current_question.answer:
            self.correct += 1

    def next_question(self):

        example_molecules = random.sample(self.mdb.molecules, 4)

        correct_idx = random.randint(0, 3)

        self.current_question = MultipleChoice(
            question="What is target of this molecule?",
            display=example_molecules[correct_idx],
            choices=[mol.target for mol in example_molecules],
            answer=correct_idx,
        )

        self.display_question()
        self.display_options()

        check_answer_button = tk.Button(
            self.frame, text="Check My Answer", command=self.check_answer, width=20
        )
        check_answer_button.place(x=350, y=400)


class MainWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ChemCards")
        self.geometry("800x600")

    def make_buttons(self):
        self.quit_button = tk.Button(
            self,
            text="Quit",
            command=self.destroy,
            width=5,
            bg="black",
            fg="white",
            font=("ariel", 16, " bold"),
        )

        # placing the Quit button on the screen
        self.quit_button.place(x=700, y=50)

    def destroy_buttons(self):
        self.mcq_button.destroy()

    def start_mcq(self):
        mcq = MultipleChoiceQuiz(self)
        mcq.start()
        self.destroy_buttons()

    def start(self):

        for widget in self.winfo_children():
            widget.destroy()

        self.make_buttons()

        self.mcq_button = tk.Button(
            self,
            text=MultipleChoiceQuiz.name,
            command=self.start_mcq,
            width=24,
            bg="blue",
            fg="white",
            font=("helvetica", 24, "bold"),
        )

        self.mcq_button.place(x=350, y=380)

        self.mainloop()
