import flet as ft
from src.services.auth_service import AuthService

# MUDANÇA: Herda de ft.Container em vez de ft.UserControl
class LoginPage(ft.Container):
    def __init__(self, page: ft.Page, on_login_success):
        super().__init__()
        self.page_ref = page  # Guardamos referencia como page_ref para evitar conflito
        self.on_login_success = on_login_success
        self.auth_service = AuthService()

        # Configurações do próprio Container (antigo build)
        self.padding = 30
        self.alignment = ft.alignment.center
        
        # --- Criação dos Controles ---
        self.txt_email = ft.TextField(
            label="E-mail", 
            prefix_icon=ft.Icons.EMAIL,
            autofocus=True,
            on_submit=lambda e: self.txt_pass.focus()
        )
        self.txt_pass = ft.TextField(
            label="Senha", 
            password=True, 
            can_reveal_password=True,
            prefix_icon=ft.Icons.LOCK,
            on_submit=self.attempt_login
        )
        
        self.btn_login = ft.ElevatedButton(
            text="Entrar",
            icon=ft.Icons.LOGIN,
            style=ft.ButtonStyle(
                padding=20,
                shape=ft.RoundedRectangleBorder(radius=8),
                bgcolor=ft.Colors.BLUE_700,
                color=ft.Colors.WHITE,
            ),
            width=200,
            on_click=self.attempt_login
        )

        # Conteúdo do Container
        self.content = ft.Column(
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,
            width=400,
            controls=[
                ft.Icon(ft.Icons.NATURE_PEOPLE, size=80, color=ft.Colors.BLUE_800),
                ft.Text("Gestão FAC", size=30, weight="bold", color=ft.Colors.BLUE_900),
                ft.Text("Acesso Restrito", size=14, color=ft.Colors.GREY_600),
                ft.Divider(height=40, color=ft.Colors.TRANSPARENT),
                self.txt_email,
                self.txt_pass,
                ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
                self.btn_login,
            ]
        )

    def attempt_login(self, e):
        email = self.txt_email.value
        password = self.txt_pass.value

        if not email or not password:
            self.show_error("Preencha todos os campos.")
            return

        self.btn_login.disabled = True
        self.update()

        if self.auth_service.authenticate(email, password):
            self.on_login_success()
        else:
            self.show_error("E-mail ou senha inválidos.")
            self.btn_login.disabled = False
            self.update()

    def show_error(self, msg):
        self.page_ref.snack_bar = ft.SnackBar(
            content=ft.Text(msg), 
            bgcolor=ft.Colors.RED_600
        )
        self.page_ref.snack_bar.open = True
        self.page_ref.update()