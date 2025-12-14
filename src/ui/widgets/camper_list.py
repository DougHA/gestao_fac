import flet as ft
from typing import List
from src.models.campista import Camper, CamperStatus
from src.data.campista_repository import CamperRepository
from src.services.auth_service import AuthService
from src.models.usuario import UserRole

class CamperList(ft.Column):
    def __init__(self, page: ft.Page):
        super().__init__()
        self.page_ref = page
        self.repository = CamperRepository()
        self.auth_service = AuthService()
        self.campers: List[Camper] = []
        
        # Configuração da Coluna principal
        self.expand = True

        # --- UI Components ---
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

        # Adiciona diretamente aos controls da classe (que é uma Column)
        self.controls = [
            ft.Container(content=self.txt_search, padding=ft.padding.only(bottom=10)),
            self.lbl_status,
            self.list_view,
        ]

    def did_mount(self):
        self.load_data()

    def load_data(self, query: str = ""):
        try:
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

    def render_list(self):
        self.list_view.controls.clear()
        
        if not self.campers:
            self.lbl_status.value = "Nenhum resultado."
            self.lbl_status.visible = True
        else:
            self.lbl_status.visible = False
            for camper in self.campers:
                card = ft.Card(
                    elevation=2,
                    content=ft.Container(
                        padding=10,
                        content=ft.ListTile(
                            leading=ft.Icon(ft.Icons.PERSON, color=self.get_status_color(camper.status), size=40),
                            title=ft.Text(camper.full_name, weight="bold"),
                            subtitle=ft.Column([
                                ft.Text(f"Apelido: {camper.nickname or '-'}", size=12),
                                ft.Text(f"Status: {camper.status.upper()}", size=10, color=ft.Colors.GREY_700)
                            ]),
                            trailing=ft.Icon(ft.Icons.INFO_OUTLINE),
                            # Ao clicar, abrimos o Modal Seguro
                            on_click=lambda _, c=camper: self.open_secure_details(c)
                        )
                    )
                )
                self.list_view.controls.append(card)
        self.update()

    # --- LÓGICA DE SEGURANÇA (RBAC) ---

    def can_view_sensitive_data(self) -> bool:
        """Verifica se o usuário atual tem permissão para ver dados sensíveis"""
        user = self.auth_service.get_current_user()
        if not user: return False
        
        # Lista de Roles permitidas
        allowed_roles = [UserRole.COORD_GERAL, UserRole.COORD_EQUIPE, UserRole.SAUDE]
        return user.role in allowed_roles

    def open_secure_details(self, camper: Camper):
        """Constrói e abre o modal de detalhes aplicando filtros de visualização"""
        
        has_permission = self.can_view_sensitive_data()

        # 1. Conteúdo Básico (Visível para TODOS)
        content_controls = [
            ft.Text("Dados Gerais", weight="bold", size=16),
            ft.TextField(label="Nome", value=camper.full_name, read_only=True),
            ft.TextField(label="Apelido", value=camper.nickname or "-", read_only=True),
            ft.TextField(label="Data Nasc.", value=str(camper.birth_date), read_only=True),
        ]

        # 2. Conteúdo Sensível (Renderização Condicional)
        if has_permission:
            sensitive_controls = [
                ft.Divider(),
                ft.Text("🔒 Dados Sensíveis (Acesso Autorizado)", weight="bold", size=16, color=ft.Colors.RED_700),
                
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
            # Feedback visual para quem não tem acesso
            content_controls.extend([
                ft.Divider(),
                ft.Container(
                    bgcolor=ft.Colors.GREY_200,
                    padding=10,
                    border_radius=5,
                    content=ft.Row([
                        ft.Icon(ft.Icons.LOCK, color=ft.Colors.GREY_500),
                        ft.Text("Dados sensíveis ocultos para o seu perfil.", color=ft.Colors.GREY_600, italic=True)
                    ])
                )
            ])

        # 3. Montagem do Modal
        dlg = ft.AlertDialog(
            title=ft.Text(f"Detalhes: {camper.nickname or camper.full_name}"),
            content=ft.Container(
                width=500, # Largura ideal para tablet/desktop, adapta-se no mobile
                content=ft.Column(
                    controls=content_controls,
                    scroll=ft.ScrollMode.AUTO,
                    height=400 # Altura fixa com scroll interno
                )
            ),
            actions=[
                ft.TextButton("Fechar", on_click=lambda e: self.close_dialog(dlg))
            ],
        )

        self.page_ref.dialog = dlg
        dlg.open = True
        self.page_ref.update()

    def close_dialog(self, dlg):
        dlg.open = False
        self.page_ref.update()