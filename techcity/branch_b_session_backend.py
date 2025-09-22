from django.contrib.sessions.backends.db import SessionStore as DBStore
from apps.company.models import BranchBSession 

class SessionStore(DBStore):
    @classmethod
    def get_model_class(cls):
        return BranchBSession
