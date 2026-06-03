from dev_env.settings import *  # noqa: F403


DJANGO_LEDGER_PURCHASEORDERMODEL_MODEL = 'swappable_purchase_order_app.CustomPurchaseOrderModel'

INSTALLED_APPS = [  # noqa: F405
    *INSTALLED_APPS,
    'django_ledger.tests.swappable_purchase_order_app.apps.SwappablePurchaseOrderAppConfig',
]
