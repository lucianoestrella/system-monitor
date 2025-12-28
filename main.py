import sys
import subprocess
import customtkinter as ctk

class ModernLauncher(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("System Monitor - Seletor")
        self.geometry("500x350")
        self.resizable(False, False)
        
        # Tema
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # Título
        self.label = ctk.CTkLabel(
            self,
            text="System Monitor",
            font=("Roboto", 24, "bold")
        )
        self.label.pack(pady=(30, 10))

        self.sublabel = ctk.CTkLabel(
            self,
            text="Escolha o modo de operação",
            font=("Roboto", 14)
        )
        self.sublabel.pack(pady=(0, 30))

        # Botão Interface Gráfica
        self.btn_gui = ctk.CTkButton(
            self,
            text="MODO GRÁFICO (Dashboard)",
            command=self.open_gui,
            height=45,
            width=300,
            fg_color="#1f538d",
            hover_color="#14375e"
        )
        self.btn_gui.pack(pady=10)

        # Botão Interface Terminal
        self.btn_cli = ctk.CTkButton(
            self,
            text="MODO TERMINAL (CLI)",
            command=self.open_cli,
            height=45,
            width=300,
            fg_color="#22c55e",
            hover_color="#16a34a"
        )
        self.btn_cli.pack(pady=10)

        # Botão Sair
        self.btn_exit = ctk.CTkButton(
            self,
            text="Sair",
            command=self.quit,
            height=35,
            width=100,
            fg_color="#ef4444",
            hover_color="#b91c1c"
        )
        self.btn_exit.pack(pady=(30, 10))

    def open_gui(self):
        """
        Abre a GUI em um processo totalmente novo para evitar
        erros de 'invalid command name' relacionados ao Tkinter.
        """
        self.destroy()  # Fecha o launcher
        # Abre o gui.py em um novo processo Python
        subprocess.Popen([sys.executable, "gui.py"])

    def open_cli(self):
        """
        Abre a CLI no terminal atual.
        Importa e executa a CLI somente após destruir a janela Tk,
        evitando conflitos entre mainloop do Tkinter e input() da CLI.
        """
        self.destroy()
        from cli import main_menu
        main_menu()


if __name__ == "__main__":
    # Permite iniciar direto em modo CLI via: python main.py --cli
    if len(sys.argv) > 1 and sys.argv[1] == "--cli":
        from cli import main_menu
        main_menu()
    else:
        app = ModernLauncher()
        app.mainloop()