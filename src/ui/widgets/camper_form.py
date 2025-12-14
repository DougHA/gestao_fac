import flet as ft
from datetime import datetime
import traceback

# Importações da nossa arquitetura
from src.models.campista import Camper, CamperStatus
from src.data.campista_repository import CamperRepository

class CamperForm(ft.Column):
    def __init__(self, page: ft.Page):
        super().__init__()
        self.page_ref = page
        self.repository = CamperRepository()
        self.selected_birth_date = None
        
        # Configuração da Coluna (Layout)
        self.scroll = ft.ScrollMode.AUTO
        self.expand = True

        # --- 1. Definição dos Campos (Igual ao anterior) ---
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
            width=200
        )
        
        self.loading_indicator = ft.ProgressBar(width=None, visible=False, color=ft.Colors.BLUE_700)

        # --- 2. Adicionando controles à lista da Coluna (self.controls) ---
        self.controls = [
            ft.Text("Ficha de Cadastro", size=24, weight="bold", color=ft.Colors.BLUE_900),
            ft.Divider(),
            
            ft.Text("Dados Básicos", weight="bold", color=ft.Colors.GREY_700),
            ft.ResponsiveRow([
                ft.Column(col={"xs": 12, "md": 8}, controls=[self.txt_full_name]),
                ft.Column(col={"xs": 12, "md": 4}, controls=[self.txt_nickname]),
            ]),
            
            ft.ResponsiveRow([
                ft.Column(col={"xs": 12, "md": 6}, controls=[self.dd_gender]),
                ft.Column(col={"xs": 12, "md": 6}, controls=[self.txt_birth_date]),
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

    # --- 3. Lógica de UI e Negócio ---

    def open_date_picker(self, e):
        """Abre o seletor nativo de data"""
        date_picker = ft.DatePicker(
            on_change=self.on_date_change,
            first_date=datetime(1990, 1, 1),
            last_date=datetime(2030, 12, 31),
        )
        self.page_ref.open(date_picker)

    def on_date_change(self, e):
        """Callback quando a data é escolhida"""
        if e.control.value:
            self.selected_birth_date = e.control.value
            # Formata para padrão brasileiro visualmente
            self.txt_birth_date.value = e.control.value.strftime("%d/%m/%Y")
            self.txt_birth_date.error_text = None # Limpa erro se houver
            self.update()


    def validate(self) -> bool:
        """Validação básica de campos obrigatórios"""
        is_valid = True
        
        # Reset errors
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

    def save_camper(self, e):
        if not self.validate():
            return

        # UI: Estado de Loading
        self.btn_save.disabled = True
        self.loading_indicator.visible = True
        self.update()

        try:
            # Construção do Modelo
            # Nota: O ID e os Timestamps são gerados automaticamente pelo SyncModel
            new_camper = Camper(
                full_name=self.txt_full_name.value,
                nickname=self.txt_nickname.value,
                gender=self.dd_gender.value,
                birth_date=self.selected_birth_date, # Python Date object
                
                # Dados Sensíveis
                document_cpf=self.txt_cpf.value,
                contact_phone=self.txt_phone.value,
                responsible_name=self.txt_responsible.value,
                medical_allergies=self.txt_allergies.value,
                medical_medications=self.txt_medications.value,
                
                # Status inicial
                status=CamperStatus.INSCRITO
            )

            # Persistência via Repository
            saved_camper = self.repository.save(new_camper)
            
            # Feedback de Sucesso
            self.show_snack(f"Campista {saved_camper.full_name} salvo com sucesso!", is_error=False)
            self.clear_form()

        except Exception as ex:
            # Log de erro para debug (print no console do dev)
            traceback.print_exc()
            # Feedback Visual para o usuário
            self.show_snack(f"Erro ao salvar: {str(ex)}", is_error=True)
        
        finally:
            # UI: Reset do estado de Loading
            self.btn_save.disabled = False
            self.loading_indicator.visible = False
            self.update()

    def clear_form(self):
        """Limpa os campos para novo cadastro"""
        self.txt_full_name.value = ""
        self.txt_nickname.value = ""
        self.dd_gender.value = None
        self.txt_birth_date.value = ""
        self.selected_birth_date = None
        self.txt_cpf.value = ""
        self.txt_phone.value = ""
        self.txt_responsible.value = ""
        self.txt_allergies.value = ""
        self.txt_medications.value = ""
        self.update()

    def show_snack(self, message: str, is_error: bool):
        snack = ft.SnackBar(
            content=ft.Text(message, color=ft.Colors.WHITE),
            bgcolor=ft.Colors.RED_600 if is_error else ft.Colors.GREEN_700,
        )
        self.page_ref.overlay.append(snack)
        snack.open = True
        self.page_ref.update()