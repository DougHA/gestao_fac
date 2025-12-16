import flet as ft
from src.models.team import Team
from src.data.team_repository import TeamRepository

class TeamManager(ft.Column):
    def __init__(self, page: ft.Page):
        super().__init__()
        self.page_ref = page
        self.repository = TeamRepository()
        self.editing_id = None
        self.expand = True

        # --- UI: Lista de Equipes ---
        self.list_view = ft.ListView(expand=True, spacing=10, padding=10)
        
        self.btn_add = ft.IconButton(
            icon=ft.Icons.ADD_CIRCLE, 
            icon_color=ft.Colors.BLUE_700, 
            icon_size=40,
            tooltip="Nova Equipe",
            on_click=lambda e: self.open_dialog()
        )

        self.controls = [
            ft.Row([
                ft.Text("Gestão de Equipes", size=20, weight="bold", color=ft.Colors.BLUE_900),
                ft.Container(expand=True),
                self.btn_add 
            ]),
            ft.Divider(),
            self.list_view,
        ]

        # --- UI: Campos do Dialog (Instanciados uma vez para reuso) ---
        self.txt_name = ft.TextField(label="Nome da Equipe *", autofocus=True)
        self.txt_desc = ft.TextField(label="Lema / Descrição")
        
        self.dd_color = ft.Dropdown(
            label="Cor da Equipe",
            options=[
                ft.dropdown.Option("#D32F2F", "Vermelho"),
                ft.dropdown.Option("#1976D2", "Azul"),
                ft.dropdown.Option("#FBC02D", "Amarelo"),
                ft.dropdown.Option("#388E3C", "Verde"),
                ft.dropdown.Option("#7B1FA2", "Roxo"),
                ft.dropdown.Option("#E64A19", "Laranja"),
                ft.dropdown.Option("#455A64", "Cinza (Staff)"),
                ft.dropdown.Option("#000000", "Preto"),
            ],
            value="#D32F2F"
        )
        # O dialog será criado dinamicamente no open_dialog para garantir atualização

    def did_mount(self):
        self.load_teams()

    def load_teams(self):
        self.list_view.controls.clear()
        teams = self.repository.list_all()
        
        for team in teams:
            self.list_view.controls.append(
                ft.Card(
                    content=ft.ListTile(
                        leading=ft.Icon(ft.Icons.CIRCLE, color=team.color_hex, size=40),
                        title=ft.Text(team.name, weight="bold"),
                        subtitle=ft.Text(team.description or "Sem descrição"),
                        trailing=ft.PopupMenuButton(
                            icon=ft.Icons.MORE_VERT,
                            items=[
                                ft.PopupMenuItem(
                                    text="Editar", 
                                    icon=ft.Icons.EDIT, 
                                    on_click=lambda _, t=team: self.open_dialog(t)
                                ),
                                ft.PopupMenuItem(
                                    text="Excluir", 
                                    icon=ft.Icons.DELETE, 
                                    on_click=lambda _, t=team: self.delete_team(t)
                                ),
                            ]
                        )
                    )
                )
            )
        self.update()

    def open_dialog(self, team: Team = None):
        """Abre o modal usando a nova sintaxe page.open()"""
        if team:
            self.editing_id = team.id
            self.txt_name.value = team.name
            self.txt_desc.value = team.description
            self.dd_color.value = team.color_hex
            title = "Editar Equipe"
        else:
            self.editing_id = None
            self.txt_name.value = ""
            self.txt_desc.value = ""
            self.dd_color.value = "#D32F2F"
            title = "Nova Equipe"

        # Recria o objeto AlertDialog para garantir estado limpo
        self.dialog = ft.AlertDialog(
            title=ft.Text(title),
            content=ft.Column([
                self.txt_name,
                self.dd_color,
                self.txt_desc
            ], tight=True, width=400),
            actions=[
                ft.TextButton("Cancelar", on_click=self.close_dialog),
                ft.ElevatedButton("Salvar", on_click=self.save_team),
            ],
        )
        
        # --- CORREÇÃO: Nova forma de abrir Dialogs ---
        self.page_ref.open(self.dialog)

    def close_dialog(self, e):
        # --- CORREÇÃO: Nova forma de fechar Dialogs ---
        self.page_ref.close(self.dialog)

    def save_team(self, e):
        if not self.txt_name.value:
            self.txt_name.error_text = "Nome obrigatório"
            self.txt_name.update()
            return

        try:
            team_data = {
                "name": self.txt_name.value,
                "color_hex": self.dd_color.value,
                "description": self.txt_desc.value,
            }

            if self.editing_id:
                existing = self.repository.get_by_id(self.editing_id)
                team = Team(
                    id=self.editing_id,
                    created_at=existing.created_at,
                    **team_data
                )
            else:
                team = Team(**team_data)

            self.repository.save(team)
            
            # Fecha o dialog antes de atualizar a lista
            self.close_dialog(None)
            self.load_teams()
            
            self.page_ref.snack_bar = ft.SnackBar(ft.Text("Equipe salva!"), bgcolor=ft.Colors.GREEN)
            self.page_ref.snack_bar.open = True
            self.page_ref.update()

        except Exception as ex:
            print(ex)

    def delete_team(self, team: Team):
        self.repository.soft_delete(team.id)
        self.load_teams()
        self.page_ref.snack_bar = ft.SnackBar(ft.Text("Equipe excluída."), bgcolor=ft.Colors.RED)
        self.page_ref.snack_bar.open = True
        self.page_ref.update()