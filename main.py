import flet as ft
from src.data.db_context import create_connection
from src.services.auth_service import AuthService
from src.ui.pages.login_page import LoginPage
from src.ui.widgets.camper_form import CamperForm
from src.ui.widgets.camper_list import CamperList
from src.models.usuario import User, UserRole

def main(page: ft.Page):
    page.title = "Gestão Acampamento FAC"
    page.theme_mode = ft.ThemeMode.LIGHT
    
    # 1. Setup Inicial
    # Garante que tabelas existam e cria o Admin se necessário
    try:
        conn = create_connection()
        # Importante: SQLModel precisa 'ver' os modelos para criar as tabelas
        # Assegure-se de importar os models (Usuario, Campista) antes disso no código real
        conn.close() 
        
        auth = AuthService()
        auth.create_admin_if_empty() # Seed inicial
    except Exception as e:
        page.add(ft.Text(f"Erro de Setup: {e}", color="red"))
        return

    # 2. Definição das Views (Telas)
    
    def route_change(route):
        page.views.clear()
        
        # Rota: LOGIN
        if page.route == "/login":
            page.views.append(
                ft.View(
                    "/login",
                    [LoginPage(page, on_login_success=lambda: page.go("/"))],
                    vertical_alignment=ft.MainAxisAlignment.CENTER,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER
                )
            )
        
        # Rota: HOME (App Principal)
        elif page.route == "/":
            current_user = auth.get_current_user()
            
            # Proteção de Rota: Se não logado, manda pro login
            if not current_user:
                page.go("/login")
                return

            # Construção da UI Principal (Tabs)
            # Verifica permissões para montar a UI
            can_edit = current_user.role in [UserRole.COORD_GERAL, UserRole.COORD_EQUIPE]
            
            tabs = []
            
            # Aba Consulta (Todos veem)
            tabs.append(ft.Tab(text="Consulta", icon=ft.Icons.LIST, content=CamperList(page)))
            
            # Aba Cadastro (Só Coordenação vê)
            if can_edit:
                tabs.append(ft.Tab(text="Cadastro", icon=ft.Icons.PERSON_ADD, content=CamperForm(page)))

            page.views.append(
                ft.View(
                    "/",
                    [
                        ft.AppBar(
                            title=ft.Text(f"Olá, {current_user.full_name}"),
                            bgcolor=ft.Colors.BLUE_700,
                            color=ft.Colors.WHITE,
                            actions=[
                                ft.IconButton(ft.Icons.LOGOUT, on_click=logout_click)
                            ]
                        ),
                        ft.Tabs(tabs=tabs, expand=True)
                    ]
                )
            )
        
        page.update()

    def view_pop(view):
        page.views.pop()
        top_view = page.views[-1]
        page.go(top_view.route)

    def logout_click(e):
        auth.logout()
        page.go("/login")

    # Configuração de rotas da página
    page.on_route_change = route_change
    page.on_view_pop = view_pop
    
    # Inicia no login ou home
    page.go("/login")

if __name__ == "__main__":
    ft.app(target=main)