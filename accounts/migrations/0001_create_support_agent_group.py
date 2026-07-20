from django.db import migrations


def create_support_agent_group(apps, schema_editor):
    group_model = apps.get_model("auth", "Group")
    group_model.objects.get_or_create(name="Support Agent")


def remove_support_agent_group(apps, schema_editor):
    group_model = apps.get_model("auth", "Group")
    group_model.objects.filter(name="Support Agent").delete()


class Migration(migrations.Migration):
    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.RunPython(
            create_support_agent_group,
            remove_support_agent_group,
        ),
    ]