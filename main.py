import flet as ft
from src.data.db_context import create_connection
from src.services.auth_service import AuthService
from src.ui.pages.login_page import LoginPage
from src.ui.widgets.camper_form import CamperForm
from src.ui.widgets.camper_list import CamperList
from src.models.usuario import User, UserRole
from src.services.sync_manager import SyncManager
import threading

def main(page: ft.Page):
    page.title = "Gestão Acampamento FAC"
    page.theme_mode = ft.ThemeMode.LIGHT
    
    # --- Configurações Iniciais ---
    try:
        conn = create_connection()
        conn.close() 
        auth = AuthService()
        auth.create_admin_if_empty() 
    except Exception as e:
        page.add(ft.Text(f"Erro de Setup: {e}", color="red"))
        return
    
    sync_service = SyncManager()

    # --- Roteamento ---
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
            can_edit = current_user.role in [UserRole.COORD_GERAL, UserRole.COORD_EQUIPE]

            # --- Definição dos Componentes ---
            
            # Referência para o TabControl para podermos mudar a aba via código
            tabs_control = ft.Tabs(expand=True, animation_duration=300)

            # Callback: Quando salvar/excluir, volta para a lista e recarrega
            def on_form_action_success():
                # Recarrega a lista
                if hasattr(lista_view, 'load_data'):
                    lista_view.load_data()
                # Muda para aba de lista (Index 0 ou 1 dependendo da ordem)
                # Como definimos ordem abaixo: 0=Lista, 1=Cadastro. 
                # Se for só servo: 0=Lista.
                tabs_control.selected_index = 0
                page.update()

            # Callback: Quando clicar em editar na lista
            def on_edit_request(camper):
                if can_edit:
                    # Carrega dados no form
                    form_view.set_camper(camper)
                    # Muda para aba de cadastro
                    tabs_control.selected_index = 1
                    page.update()

            # Instanciando Views
            lista_view = CamperList(page, on_edit_click=on_edit_request)
            form_view = CamperForm(page, on_save_success=on_form_action_success)

            # --- Montagem das Abas ---
            my_tabs = []
            
            # Aba 1: Consulta (Sempre visível)
            my_tabs.append(ft.Tab(text="Consulta", icon=ft.Icons.LIST, content=lista_view))
            
            # Aba 2: Cadastro (Só Coordenação)
            if can_edit:
                my_tabs.append(ft.Tab(text="Cadastro / Edição", icon=ft.Icons.EDIT_DOCUMENT, content=form_view))

            tabs_control.tabs = my_tabs

            # --- Função de Sync ---
            def run_sync(e):
                btn_sync.disabled = True
                btn_sync.text = "Sincronizando..."
                page.update()

                def worker():
                    result = sync_service.perform_sync()
                    
                    status_msg = ""
                    if result["status"] == "success":
                        status_msg = f"Sync OK! ▲{result['pushed']} ▼{result['pulled']}"
                        icon = ft.Icons.CLOUD_DONE
                        color = ft.Colors.GREEN
                    elif result["status"] == "offline":
                        status_msg = "Offline. Operando localmente."
                        icon = ft.Icons.WIFI_OFF
                        color = ft.Colors.ORANGE_700 # Laranja mais escuro para visibilidade
                    else:
                        status_msg = f"Erro: {result['errors'][0]}"
                        icon = ft.Icons.ERROR
                        color = ft.Colors.RED

                    btn_sync.text = "Sincronizar"
                    btn_sync.icon = icon
                    # Dica visual no botão se estiver offline
                    btn_sync.bgcolor = ft.Colors.ORANGE_100 if result["status"] == "offline" else None
                    btn_sync.color = ft.Colors.ORANGE_900 if result["status"] == "offline" else None
                    
                    btn_sync.disabled = False
                    
                    page.snack_bar = ft.SnackBar(ft.Text(status_msg), bgcolor=color)
                    page.snack_bar.open = True
                    page.update()

                threading.Thread(target=worker, daemon=True).start()

            # Botão Sync
            btn_sync = ft.ElevatedButton(
                "Sincronizar", 
                icon=ft.Icons.CLOUD_SYNC, 
                on_click=run_sync
            )

            # View Principal
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