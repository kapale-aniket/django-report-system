from dataclasses import dataclass


@dataclass(frozen=True)
class UserProfile:
    id: int
    username: str
    email: str
    role: str
    department: str
    roll_number: str
    is_active: bool

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'role': self.role,
            'department': self.department,
            'roll_number': self.roll_number,
            'is_active': self.is_active,
        }
