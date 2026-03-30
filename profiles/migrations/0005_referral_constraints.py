from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("profiles", "0004_alter_profile_referral_code"),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name="referral",
            unique_together=set(),
        ),
        migrations.AddConstraint(
            model_name="referral",
            constraint=models.UniqueConstraint(
                fields=("referrer", "referred_user"),
                name="uq_referral_referrer_referred",
            ),
        ),
        migrations.AddConstraint(
            model_name="referral",
            constraint=models.UniqueConstraint(
                fields=("referred_user",),
                name="uq_referral_referred_once",
            ),
        ),
        migrations.AddConstraint(
            model_name="referral",
            constraint=models.CheckConstraint(
                check=models.Q(("referrer", models.F("referred_user")), _negated=True),
                name="ck_referral_not_self",
            ),
        ),
        migrations.AddIndex(
            model_name="referral",
            index=models.Index(fields=["referrer", "created_at"], name="profiles_refer_referrer_4532db_idx"),
        ),
        migrations.AddIndex(
            model_name="referral",
            index=models.Index(fields=["referred_user"], name="profiles_refer_referred_8e9f0a_idx"),
        ),
    ]
