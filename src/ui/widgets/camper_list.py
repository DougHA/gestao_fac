import flet as ft
from typing import List, Dict
from src.models.campista import Camper, CamperStatus
from src.models.team import Team # Importação do Modelo
from src.data.campista_repository import CamperRepository
from src.data.team_repository import TeamRepository # Importação do Repo
from src.services.auth_service import AuthService
from src.models.usuario import UserRole

class CamperList(ft.Column):
    def __init__(self, page: ft.Page, on_edit_click=None):
        super().__init__()
        self.page_ref = page
        self.on_edit_click = on_edit_click
        
        self.repository = CamperRepository()
        self.team_repository = TeamRepository() # Repositório de Equipes
        self.auth_service = AuthService()
        
        self.campers: List[Camper] = []
        self.teams_map: Dict[str, Team] = {} # Mapa para acesso rápido (Cache)
        
        # Variáveis para controle dos Dialogs
        self.camper_to_delete = None 
        self.dlg_delete = None
        self.dlg_details = None
        
        self.expand = True
        
        self.txt_search = ft.TextField(
            label="Buscar Campista",
            hint_text="Nome, Apelido ou Equipe",
            prefix_icon=ft.Icons.SEARCH,
            on_change=self.on_search_change,
            border_radius=10
        )

        self.list_view = ft.ListView(
            expand=True, 
            spacing=10, 
            padding=10
        )
        
        self.lbl_status = ft.Text("Carregando...", italic=True, color=ft.Colors.GREY_500)

        self.controls = [
            ft.Container(content=self.txt_search, padding=ft.padding.only(bottom=10)),
            self.lbl_status,
            self.list_view,
        ]

    def did_mount(self):
        # Carrega as equipes primeiro para mapear IDs -> Nomes/Cores
        self.load_teams_cache()
        self.load_data()

    def load_teams_cache(self):
        """Carrega todas as equipes para memória para exibição rápida"""
        try:
            all_teams = self.team_repository.list_all()
            # Cria um dicionário: { "id_da_equipe": ObjetoTeam }
            self.teams_map = {str(t.id): t for t in all_teams}
        except Exception:
            self.teams_map = {}

    def load_data(self, query: str = ""):
        try:
            # Recarrega o cache de equipes para garantir consistência se houve sync
            self.load_teams_cache()
            self.campers = self.repository.search_campers(query)
            self.render_list()
        except Exception as e:
            self.lbl_status.value = f"Erro: {e}"
            self.lbl_status.visible = True
            self.update()

    def on_search_change(self, e):
        self.load_data(e.control.value)

    def get_status_color(self, status: str):
        colors = {
            CamperStatus.ATIVO: ft.Colors.GREEN,
            CamperStatus.CHECK_IN: ft.Colors.BLUE,
            CamperStatus.INSCRITO: ft.Colors.GREY,
            CamperStatus.ENCERRADO: ft.Colors.RED,
        }
        return colors.get(status, ft.Colors.GREY)

    def can_edit_data(self) -> bool:
        user = self.auth_service.get_current_user()
        if not user: return False
        allowed_roles = [UserRole.COORD_GERAL, UserRole.COORD_EQUIPE]
        return user.role in allowed_roles

    def render_list(self):
        self.list_view.controls.clear()
        
        has_edit_permission = self.can_edit_data()

        if not self.campers:
            self.lbl_status.value = "Nenhum resultado."
            self.lbl_status.visible = True
        else:
            self.lbl_status.visible = False
            for camper in self.campers:
                
                # --- LÓGICA DA EQUIPE ---
                team_info_control = ft.Container() # Vazio por padrão
                
                if camper.team_id and str(camper.team_id) in self.teams_map:
                    team = self.teams_map[str(camper.team_id)]
                    team_info_control = ft.Container(
                        content=ft.Text(team.name, size=10, color=ft.Colors.WHITE, weight="bold"),
                        bgcolor=team.color_hex,
                        padding=ft.padding.symmetric(horizontal=8, vertical=2),
                        border_radius=10,
                        margin=ft.margin.only(top=5)
                    )
                else:
                     # Se não tiver equipe, mostra um aviso discreto
                     team_info_control = ft.Container(
                        content=ft.Text("Sem Equipe", size=10, color=ft.Colors.GREY_500),
                        padding=ft.padding.symmetric(horizontal=8, vertical=2),
                        border=ft.border.all(1, ft.Colors.GREY_300),
                        border_radius=10,
                        margin=ft.margin.only(top=5)
                    )

                # --- MENU DE AÇÕES ---
                menu_items = [
                    ft.PopupMenuItem(
                        text="Detalhes / Ficha",
                        icon=ft.Icons.INFO,
                        on_click=lambda _, c=camper: self.open_secure_details(c)
                    )
                ]

                if has_edit_permission:
                    menu_items.append(ft.PopupMenuItem(
                        text="Editar",
                        icon=ft.Icons.EDIT,
                        on_click=lambda _, c=camper: self.trigger_edit_direct(c)
                    ))
                    menu_items.append(ft.PopupMenuItem(
                        text="Excluir",
                        icon=ft.Icons.DELETE,
                        on_click=lambda _, c=camper: self.confirm_delete_request(c)
                    ))

                card = ft.Card(
                    elevation=2,
                    content=ft.Container(
                        padding=10,
                        content=ft.ListTile(
                            leading=ft.Icon(ft.Icons.PERSON, color=self.get_status_color(camper.status), size=40),
                            title=ft.Text(camper.full_name, weight="bold"),
                            subtitle=ft.Column([
                                ft.Text(f"Apelido: {camper.nickname or '-'}", size=12),
                                ft.Row([
                                    ft.Text(f"Status: {camper.status.upper()}", size=10, color=ft.Colors.GREY_700),
                                    team_info_control # Adiciona a etiqueta da equipe aqui
                                ], alignment=ft.MainAxisAlignment.START, vertical_alignment=ft.CrossAxisAlignment.CENTER)
                            ], spacing=2),
                            trailing=ft.PopupMenuButton(
                                icon=ft.Icons.MORE_VERT,
                                items=menu_items
                            ),
                            on_click=lambda _, c=camper: self.open_secure_details(c)
                        )
                    )
                )
                self.list_view.controls.append(card)
        self.update()

    def trigger_edit_direct(self, camper):
        if self.on_edit_click:
            self.on_edit_click(camper)

    # --- EXCLUSÃO ---
    def confirm_delete_request(self, camper):
        self.camper_to_delete = camper
        self.dlg_delete = ft.AlertDialog(
            title=ft.Text("Excluir Campista"),
            content=ft.Text(f"Tem certeza que deseja excluir {camper.full_name}?"),
            actions=[
                ft.TextButton("Cancelar", on_click=self.cancel_delete),
                ft.TextButton("Excluir", on_click=self.execute_delete, style=ft.ButtonStyle(color=ft.Colors.RED)),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.page_ref.open(self.dlg_delete)

    def cancel_delete(self, e):
        if self.dlg_delete:
            self.page_ref.close(self.dlg_delete)
        self.camper_to_delete = None

    def execute_delete(self, e):
        if self.dlg_delete:
            self.page_ref.close(self.dlg_delete)
        
        if self.camper_to_delete:
            try:
                self.repository.soft_delete(self.camper_to_delete.id)
                
                self.page_ref.snack_bar = ft.SnackBar(ft.Text("Campista excluído com sucesso!"), bgcolor=ft.Colors.GREEN)
                self.page_ref.snack_bar.open = True
                self.page_ref.update()
                
                self.load_data(self.txt_search.value)
                
            except Exception as ex:
                self.page_ref.snack_bar = ft.SnackBar(ft.Text(f"Erro: {ex}"), bgcolor=ft.Colors.RED)
                self.page_ref.snack_bar.open = True
                self.page_ref.update()
            
            finally:
                self.camper_to_delete = None

    # --- DETALHES ---
    def can_view_sensitive_data(self) -> bool:
        user = self.auth_service.get_current_user()
        if not user: return False
        allowed_roles = [UserRole.COORD_GERAL, UserRole.COORD_EQUIPE, UserRole.SAUDE]
        return user.role in allowed_roles

    def open_secure_details(self, camper: Camper):
        has_permission_view = self.can_view_sensitive_data()
        
        # Lógica para mostrar nome da equipe no modal também
        team_name = "Sem Equipe"
        if camper.team_id and str(camper.team_id) in self.teams_map:
             team_name = self.teams_map[str(camper.team_id)].name

        content_controls = [
            ft.Text("Dados Gerais", weight="bold", size=16),
            ft.TextField(label="Nome", value=camper.full_name, read_only=True),
            ft.TextField(label="Apelido", value=camper.nickname or "-", read_only=True),
            ft.TextField(label="Equipe", value=team_name, read_only=True), # Mostra equipe aqui
            ft.TextField(label="Data Nasc.", value=str(camper.birth_date), read_only=True),
        ]

        if has_permission_view:
            sensitive_controls = [
                ft.Divider(),
                ft.Text("🔒 Dados Sensíveis", weight="bold", size=16, color=ft.Colors.RED_700),
                
                ft.ResponsiveRow([
                    ft.Column(col=6, controls=[ft.TextField(label="CPF", value=camper.document_cpf or "N/A", read_only=True)]),
                    ft.Column(col=6, controls=[ft.TextField(label="Telefone", value=camper.contact_phone or "N/A", read_only=True)]),
                ]),
                
                ft.Text("Saúde & Cuidados", weight="bold", color=ft.Colors.GREY_700),
                ft.TextField(label="Alergias", value=camper.medical_allergies or "Nenhuma", read_only=True, multiline=True),
                ft.TextField(label="Medicações", value=camper.medical_medications or "Nenhuma", read_only=True, multiline=True),
                ft.TextField(label="Responsável", value=camper.responsible_name, read_only=True),
            ]
            content_controls.extend(sensitive_controls)
        else:
            content_controls.extend([
                ft.Divider(),
                ft.Container(
                    bgcolor=ft.Colors.GREY_200,
                    padding=10,
                    border_radius=5,
                    content=ft.Row([
                        ft.Icon(ft.Icons.LOCK, color=ft.Colors.GREY_500),
                        ft.Text("Dados sensíveis ocultos.", color=ft.Colors.GREY_600, italic=True)
                    ])
                )
            ])

        self.dlg_details = ft.AlertDialog(
            title=ft.Text(f"Detalhes: {camper.nickname or camper.full_name}"),
            content=ft.Container(
                width=500,
                content=ft.Column(
                    controls=content_controls,
                    scroll=ft.ScrollMode.AUTO,
                    height=400 
                )
            ),
            actions=[
                ft.TextButton("Fechar", on_click=lambda e: self.page_ref.close(self.dlg_details))
            ],
        )

        self.page_ref.open(self.dlg_details)