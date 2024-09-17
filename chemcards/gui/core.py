import tkinter as tk


class MainWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ChemCards")
        self.geometry("800x600")

    def start(self):
        self.mainloop()