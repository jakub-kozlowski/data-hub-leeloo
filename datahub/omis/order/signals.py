import django.dispatch


order_paid = django.dispatch.Signal(providing_args=['order'])
order_completed = django.dispatch.Signal(providing_args=['order'])
order_cancelled = django.dispatch.Signal(providing_args=['order'])

quote_generated = django.dispatch.Signal(providing_args=['order'])
quote_accepted = django.dispatch.Signal(providing_args=['order'])
quote_cancelled = django.dispatch.Signal(providing_args=['order', 'by'])
