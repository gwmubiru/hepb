from celery import shared_task
from datetime import datetime
from django.contrib.auth import get_user_model
from django.db import transaction
import traceback, os
from . import utils

LOG_FILE = "/tmp/celery_result_errors.log"

def log_error(entry, e):
    with open(LOG_FILE, "a") as f:
        f.write(f"\n--- Error processing {entry.get('SampleID')} ---\n")
        f.write(str(e) + "\n")
        traceback.print_exc(file=f)
        f.write("\n")

@shared_task
def process_alinity_result(entry):
    """
    entry: dict containing the parsed JSON record
    """
    try:
        machine_type = 'N'
        instrument_id = entry.get("SampleID")
        result = entry.get("Result")
        multiplier = 1
        User = get_user_model()
        user = User.objects.first()
        test_date = entry.get("DateTime")
        result_run = utils.get_result_run(
             f"{instrument_id}_{datetime.now().strftime('%Y%m%d')}",
            user
        )
        row_index = 3
        the_test_date = entry.get("DateTime")

        utils.update_sample_and_save_result(
            machine_type,
            instrument_id,
            result,
            multiplier,
            user,
            test_date,
            result_run,
            row_index,
            the_test_date
        )
        if result_run is None:
            print("❌ result_run is None!")
        print("🔹 DEBUG: instrument_id =", instrument_id)
        print("🔹 DEBUG: result =", result)
        print("🔹 DEBUG: test_date =", test_date)
        print("🔹 DEBUG: user =", user)
        print("🔹 DEBUG: result_run =", result_run)   
        return f"Processed sample {entry.get('SampleID')}"
    except Exception as e:
        log_error(entry, e)
        raise


