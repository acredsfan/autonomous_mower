import usb_cdc  # type:ignore
# keeps REPL on ACM0, adds data on ACM1
usb_cdc.enable(console=True, data=True)
