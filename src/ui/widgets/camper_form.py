import flet as ft
from datetime import datetime
import traceback
from src.models.campista import Camper, CamperStatus
from src.models.team import Team
from src.data.campista_repository import CamperRepository
from src.data.team_repository import TeamRepository

class CamperForm(ft.Column):
    def __init__(self, page: ft.Page, on_save_success=None):
        super().__init__()
        self.page_ref = page
        self.on_save_success = on_save_success
        self.repository = CamperRepository()
        self.team_repository = TeamRepository()
        
        self.current_camper_id = None 
        self.created_at_cache = None
        self.selected_birth_date = None
        
        self.scroll = ft.ScrollMode.AUTO
        self.expand = True

        self.lbl_title = ft.Text("Novo Cadastro", size=24, weight="bold", color=ft.Colors.BLUE_900)
        
        self.txt_full_name = ft.TextField(label="Nome Completo *", border_color=ft.Colors.GREY_400)
        self.txt_nickname = ft.TextField(label="Apelido (Crachá)", border_color=ft.Colors.GREY_400)
        
        self.dd_gender = ft.Dropdown(
            label="Gênero *",
            options=[
                ft.dropdown.Option("M", "Masculino"),
                ft.dropdown.Option("F", "Feminino"),
            ],
            border_color=ft.Colors.GREY_400
        )

        # Dropdown de Equipes
        self.dd_team = ft.Dropdown(
            label="Equipe",
            options=[],
            border_color=ft.Colors.GREY_400,
            # Quando clica no campo (foco), força atualização visual
            on_focus=lambda e: self.load_teams(update_view=True) 
        )

        self.txt_birth_date = ft.TextField(
            label="Data de Nascimento *", 
            hint_text="Selecione a data...",
            read_only=True,
            icon=ft.Icons.CALENDAR_TODAY,
            on_click=self.open_date_picker
        )

        self.txt_cpf = ft.TextField(label="CPF", keyboard_type=ft.KeyboardType.NUMBER)
        self.txt_phone = ft.TextField(label="Telefone Contato", keyboard_type=ft.KeyboardType.PHONE)
        self.txt_responsible = ft.TextField(label="Nome do Responsável")

        self.txt_allergies = ft.TextField(label="Alergias", multiline=True, min_lines=2)
        self.txt_medications = ft.TextField(label="Medicações em uso", multiline=True, min_lines=2)

        self.btn_save = ft.ElevatedButton(
            text="Salvar Campista",
            icon=ft.Icons.SAVE,
            style=ft.ButtonStyle(
                color=ft.Colors.WHITE,
                bgcolor=ft.Colors.BLUE_700,
                padding=15,
                shape=ft.RoundedRectangleBorder(radius=8),
            ),
            on_click=self.save_camper,
            expand=True
        )

        self.btn_clear = ft.OutlinedButton(
            text="Limpar / Novo",
            icon=ft.Icons.ADD,
            on_click=lambda e: self.clear_form(),
            visible=False 
        )

        self.btn_delete = ft.IconButton(
            icon=ft.Icons.DELETE,
            icon_color=ft.Colors.RED_600,
            tooltip="Excluir Campista",
            visible=False, 
            on_click=self.confirm_delete
        )
        
        self.loading_indicator = ft.ProgressBar(width=None, visible=False, color=ft.Colors.BLUE_700)

        self.controls = [
            ft.Row([
                self.lbl_title,
                ft.Container(expand=True),
                self.btn_clear,
                self.btn_delete
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            
            ft.Divider(),
            
            ft.Text("Dados Básicos", weight="bold", color=ft.Colors.GREY_700),
            ft.ResponsiveRow([
                ft.Column(col={"xs": 12, "md": 8}, controls=[self.txt_full_name]),
                ft.Column(col={"xs": 12, "md": 4}, controls=[self.txt_nickname]),
            ]),
            
            ft.ResponsiveRow([
                ft.Column(col={"xs": 12, "md": 4}, controls=[self.dd_gender]),
                ft.Column(col={"xs": 12, "md": 4}, controls=[self.dd_team]),
                ft.Column(col={"xs": 12, "md": 4}, controls=[self.txt_birth_date]),
            ]),

            ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
            ft.Text("Contato e Responsável", weight="bold", color=ft.Colors.GREY_700),
            
            ft.ResponsiveRow([
                ft.Column(col={"xs": 12, "md": 6}, controls=[self.txt_cpf]),
                ft.Column(col={"xs": 12, "md": 6}, controls=[self.txt_phone]),
                ft.Column(col={"xs": 12}, controls=[self.txt_responsible]),
            ]),

            ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
            ft.Text("Saúde", weight="bold", color=ft.Colors.GREY_700),
            
            self.txt_allergies,
            self.txt_medications,

            ft.Divider(height=30),
            
            self.loading_indicator,
            ft.Row([self.btn_save], alignment=ft.MainAxisAlignment.CENTER)
        ]
        
        # CORREÇÃO: update_view=False pois o componente ainda não está na tela
        self.load_teams(update_view=False)

    # --- Lógica de Carregamento de Equipes ---
    def load_teams(self, update_view=True):
        """Busca equipes no DB local e popula o dropdown"""
        try:
            teams = self.team_repository.list_all()
            self.dd_team.options = [
                ft.dropdown.Option(key=str(t.id), text=t.name) for t in teams
            ]
            # CORREÇÃO: Só chama update() se solicitado
            if update_view:
                self.dd_team.update()
        except Exception as e:
            print(f"Erro ao carregar equipes: {e}")

    def set_camper(self, camper: Camper):
        self.current_camper_id = camper.id
        self.created_at_cache = camper.created_at
        
        self.lbl_title.value = "Editar Campista"
        self.btn_save.text = "Atualizar Dados"
        self.btn_save.bgcolor = ft.Colors.ORANGE_700
        
        self.btn_delete.visible = True
        self.btn_clear.visible = True

        self.txt_full_name.value = camper.full_name
        self.txt_nickname.value = camper.nickname
        self.dd_gender.value = camper.gender
        
        # Carrega equipes (com update visual, pois já está na tela)
        self.load_teams(update_view=True) 
        self.dd_team.value = camper.team_id
        
        if camper.birth_date:
            self.selected_birth_date = camper.birth_date
            self.txt_birth_date.value = camper.birth_date.strftime("%d/%m/%Y")
        
        self.txt_cpf.value = camper.document_cpf
        self.txt_phone.value = camper.contact_phone
        self.txt_responsible.value = camper.responsible_name
        self.txt_allergies.value = camper.medical_allergies
        self.txt_medications.value = camper.medical_medications

        self.update()

    def clear_form(self):
        self.current_camper_id = None
        self.created_at_cache = None
        
        self.lbl_title.value = "Novo Cadastro"
        self.btn_save.text = "Salvar Campista"
        self.btn_save.bgcolor = ft.Colors.BLUE_700
        self.btn_delete.visible = False
        self.btn_clear.visible = False

        self.txt_full_name.value = ""
        self.txt_nickname.value = ""
        self.dd_gender.value = None
        self.dd_team.value = None
        self.txt_birth_date.value = ""
        self.selected_birth_date = None
        self.txt_cpf.value = ""
        self.txt_phone.value = ""
        self.txt_responsible.value = ""
        self.txt_allergies.value = ""
        self.txt_medications.value = ""
        
        self.update()

    def confirm_delete(self, e):
        dlg = ft.AlertDialog(
            title=ft.Text("Confirmar Exclusão"),
            content=ft.Text("Tem certeza? Isso removerá o campista da lista ativa."),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: self.close_dialog(dlg)),
                ft.TextButton("Excluir", on_click=self.execute_soft_delete, style=ft.ButtonStyle(color=ft.Colors.RED)),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.page_ref.open(dlg)

    def close_dialog(self, dlg):
        self.page_ref.close(dlg)

    def execute_soft_delete(self, e):
        if self.current_camper_id:
            try:
                self.repository.soft_delete(self.current_camper_id)
                self.show_snack("Campista movido para lixeira.", is_error=False)
                self.clear_form()
                if self.on_save_success:
                    self.on_save_success()
            except Exception as ex:
                self.show_snack(f"Erro ao excluir: {ex}", is_error=True)

    def save_camper(self, e):
        if not self.validate():
            return

        self.btn_save.disabled = True
        self.loading_indicator.visible = True
        self.update()

        try:
            camper_data = {
                "full_name": self.txt_full_name.value,
                "nickname": self.txt_nickname.value,
                "gender": self.dd_gender.value,
                "birth_date": self.selected_birth_date,
                "team_id": self.dd_team.value,
                "document_cpf": self.txt_cpf.value,
                "contact_phone": self.txt_phone.value,
                "responsible_name": self.txt_responsible.value,
                "medical_allergies": self.txt_allergies.value,
                "medical_medications": self.txt_medications.value,
                "status": CamperStatus.INSCRITO 
            }

            if self.current_camper_id:
                camper = Camper(
                    id=self.current_camper_id,
                    created_at=self.created_at_cache,
                    **camper_data
                )
            else:
                camper = Camper(**camper_data)

            self.repository.save(camper)
            
            action = "atualizado" if self.current_camper_id else "criado"
            self.show_snack(f"Campista {action} com sucesso!", is_error=False)
            self.clear_form()
            
            if self.on_save_success:
                self.on_save_success()

        except Exception as ex:
            traceback.print_exc()
            self.show_snack(f"Erro ao salvar: {str(ex)}", is_error=True)
        
        finally:
            self.btn_save.disabled = False
            self.loading_indicator.visible = False
            self.update()

    def open_date_picker(self, e):
        date_picker = ft.DatePicker(
            on_change=self.on_date_change,
            first_date=datetime(1990, 1, 1),
            last_date=datetime(2030, 12, 31),
        )
        self.page_ref.open(date_picker)

    def on_date_change(self, e):
        if e.control.value:
            self.selected_birth_date = e.control.value
            self.txt_birth_date.value = e.control.value.strftime("%d/%m/%Y")
            self.txt_birth_date.error_text = None 
            self.update()

    def validate(self) -> bool:
        is_valid = True
        self.txt_full_name.error_text = None
        self.dd_gender.error_text = None
        self.txt_birth_date.error_text = None

        if not self.txt_full_name.value:
            self.txt_full_name.error_text = "Nome é obrigatório"
            is_valid = False
        if not self.dd_gender.value:
            self.dd_gender.error_text = "Selecione o gênero"
            is_valid = False
        if not self.selected_birth_date:
            self.txt_birth_date.error_text = "Data de nascimento obrigatória"
            is_valid = False
        self.update()
        return is_valid

    def show_snack(self, message: str, is_error: bool):
        snack = ft.SnackBar(
            content=ft.Text(message, color=ft.Colors.WHITE),
            bgcolor=ft.Colors.RED_600 if is_error else ft.Colors.GREEN_700,
        )
        self.page_ref.overlay.append(snack)
        snack.open = True
        self.page_ref.update()