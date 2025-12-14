import hashlib
from typing import Optional
from sqlmodel import SQLModel, Session, select, create_engine
from src.data.db_context import get_db_path 
from src.models.usuario import User, UserRole

class AuthService:
    _current_user: Optional[User] = None

    def __init__(self):
        # Em produção, este SALT deve vir de variáveis de ambiente seguras
        self._salt_secret = "projeto_fac_segredo_offline_2025"
        
        # CORREÇÃO: Criamos o Engine do SQLModel em vez de usar conexão bruta
        db_path = get_db_path()
        self.engine = create_engine(
            f"sqlite:///{db_path}", 
            connect_args={"check_same_thread": False} # Necessário para Flet
        )
        SQLModel.metadata.create_all(self.engine)

    def _hash_password(self, password: str) -> str:
        """Gera hash SHA256 com salt para armazenamento seguro"""
        salted = f"{password}{self._salt_secret}"
        return hashlib.sha256(salted.encode()).hexdigest()

    def authenticate(self, email: str, password: str) -> bool:
        """Verifica credenciais no banco local SQLite"""
        try:
            # CORREÇÃO: Usamos self.engine aqui
            with Session(self.engine) as session:
                user = session.exec(select(User).where(User.email == email)).first()
                
                if not user:
                    return False
                
                # Verifica hash
                if user.password_hash == self._hash_password(password):
                    AuthService._current_user = user
                    return True
                return False
        except Exception as e:
            print(f"Erro na autenticação: {e}")
            return False

    def get_current_user(self) -> Optional[User]:
        return AuthService._current_user

    def logout(self):
        AuthService._current_user = None

    def create_admin_if_empty(self):
        """
        SEED: Cria um usuário admin padrão se o banco estiver vazio.
        Essencial para o primeiro acesso offline.
        """
        try:
            # CORREÇÃO: Usamos self.engine aqui
            with Session(self.engine) as session:
                # Verifica se existe algum usuário
                if not session.exec(select(User)).first():
                    admin = User(
                        full_name="Coordenação Geral",
                        email="admin@fac.com",
                        password_hash=self._hash_password("admin123"),
                        role=UserRole.COORD_GERAL
                    )
                    session.add(admin)
                    session.commit()
                    print("--- USUÁRIO ADMIN CRIADO: admin@fac.com / admin123 ---")
        except Exception as e:
            print(f"Erro ao criar admin seed: {e}")
            raise e