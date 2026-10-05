from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group

class Command(BaseCommand):
    help = 'Create default user roles'

    def handle(self, *args, **options):
        # Create groups for roles if they don't exist
        roles = ['admin', 'teacher', 'student', 'parent']
        
        for role in roles:
            group, created = Group.objects.get_or_create(name=role)
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Successfully created role "{role}"')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Role "{role}" already exists')
                )
        
        self.stdout.write(
            self.style.SUCCESS('Successfully created default roles')
        )
