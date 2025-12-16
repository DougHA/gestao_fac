import flet as ft
from src.data.db_context import create_connection
from src.services.auth_service import AuthService
from src.ui.pages.login_page import LoginPage
from src.ui.widgets.camper_form import CamperForm
from src.ui.widgets.camper_list import CamperList
from src.ui.widgets.team_manager import TeamManager # Importação das Equipes
from src.models.usuario import User, UserRole
from src.services.sync_manager import SyncManager
from src.data.team_repository import TeamRepository
import threading

def main(page: ft.Page):
    page.title = "Gestão Acampamento FAC"
    page.theme_mode = ft.ThemeMode.LIGHT
    
    try:
        conn = create_connection()
        conn.close() 
        auth = AuthService()
        auth.create_admin_if_empty() 
        
        # Seed inicial de equipes para garantir que não comece vazio
        TeamRepository().seed_initial_teams()
        
    except Exception as e:
        page.add(ft.Text(f"Erro de Setup: {e}", color="red"))
        return
    
    sync_service = SyncManager()

    def route_change(route):
        page.views.clear()
        
        if page.route == "/login":
            page.views.append(
                ft.View(
                    "/login",
                    [LoginPage(page, on_login_success=lambda: page.go("/"))],
                    vertical_alignment=ft.MainAxisAlignment.CENTER,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER
                )
            )
        
        elif page.route == "/":
            current_user = auth.get_current_user()
            if not current_user:
                page.go("/login")
                return

            # Permissões
            is_admin = current_user.role == UserRole.COORD_GERAL
            can_edit = current_user.role in [UserRole.COORD_GERAL, UserRole.COORD_EQUIPE]

            # --- Definição dos Callbacks ---

            def on_form_action_success():
                """Chamado quando salva/exclui campista"""
                if hasattr(lista_view, 'load_data'):
                    lista_view.load_data()
                # Volta para a aba de consulta (Index 0)
                tabs_control.selected_index = 0
                page.update()

            def on_edit_request(camper):
                """Chamado ao clicar em editar na lista"""
                if can_edit:
                    form_view.set_camper(camper)
                    # Procura qual índice é a aba de cadastro (geralmente 1)
                    # Se tiver Equipes e for admin, indices: 0=Lista, 1=Cadastro, 2=Equipes
                    tabs_control.selected_index = 1
                    page.update()

            # --- Instanciando as Views ---
            lista_view = CamperList(page, on_edit_click=on_edit_request)
            form_view = CamperForm(page, on_save_success=on_form_action_success)
            teams_view = TeamManager(page)

            # --- Lógica de Mudança de Aba ---
            def on_tab_change(e):
                # Se mudou para a aba de Cadastro (Index 1), recarrega as equipes
                # Isso garante que se criou uma equipe nova, ela aparece aqui.
                if tabs_control.selected_index == 1:
                    form_view.load_teams(update_view=True)

            # --- Montagem das Abas ---
            my_tabs = []
            my_tabs.append(ft.Tab(text="Consulta", icon=ft.Icons.LIST, content=lista_view))
            
            if can_edit:
                my_tabs.append(ft.Tab(text="Cadastro", icon=ft.Icons.PERSON_ADD, content=form_view))
            
            if is_admin:
                my_tabs.append(ft.Tab(text="Equipes", icon=ft.Icons.GROUPS, content=teams_view))

            # Controle de Abas com o Evento on_change
            tabs_control = ft.Tabs(
                tabs=my_tabs, 
                expand=True, 
                animation_duration=300,
                on_change=on_tab_change # <--- AQUI ESTÁ A CORREÇÃO MÁGICA
            )

            # --- Botão de Sync ---
            def run_sync(e):
                btn_sync.disabled = True
                btn_sync.text = "Sincronizando..."
                page.update()

                def worker():
                    result = sync_service.perform_sync()
                    
                    status_msg = ""
                    if result["status"] == "success":
                        # Mostra contadores de tudo (campistas + equipes)
                        total_pushed = result['pushed']
                        total_pulled = result['pulled']
                        status_msg = f"Sync OK! ▲{total_pushed} ▼{total_pulled}"
                        
                        icon = ft.Icons.CLOUD_DONE
                        color = ft.Colors.GREEN
                        
                        # Recarrega listas após sync para exibir dados novos
                        lista_view.load_data()
                        form_view.load_teams(update_view=True)
                        teams_view.load_teams()
                        
                    elif result["status"] == "offline":
                        status_msg = "Offline. Operando localmente."
                        icon = ft.Icons.WIFI_OFF
                        color = ft.Colors.ORANGE_700
                    else:
                        errors = result.get('errors', ['Erro desconhecido'])
                        status_msg = f"Erro: {errors[0] if errors else '?'}"
                        icon = ft.Icons.ERROR
                        color = ft.Colors.RED

                    btn_sync.text = "Sincronizar"
                    btn_sync.icon = icon
                    btn_sync.bgcolor = ft.Colors.ORANGE_100 if result["status"] == "offline" else None
                    btn_sync.color = ft.Colors.ORANGE_900 if result["status"] == "offline" else None
                    btn_sync.disabled = False
                    
                    page.snack_bar = ft.SnackBar(ft.Text(status_msg), bgcolor=color)
                    page.snack_bar.open = True
                    page.update()

                threading.Thread(target=worker, daemon=True).start()

            btn_sync = ft.ElevatedButton(
                "Sincronizar", 
                icon=ft.Icons.CLOUD_SYNC, 
                on_click=run_sync
            )

            # Layout Principal
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
                        ft.Container(content=btn_sync, padding=10),
                        tabs_control
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

    page.on_route_change = route_change
    page.on_view_pop = view_pop
    page.go("/login")

if __name__ == "__main__":
    ft.app(target=main)