from pathlib import Path


ROOT=Path(__file__).resolve().parents[1]


def test_mobile_pair_scan_keeps_camera_component_and_stream_between_labels():
    ui=(ROOT/'license_app'/'preparation_ui.py').read_text(encoding='utf-8')
    scanner=(ROOT/'license_app'/'qr_scanner'/'index.html').read_text(encoding='utf-8')

    assert "key='live-qr-pair-scan'" in ui
    assert 'scan_enabled=(next_index is not None)' in ui
    assert 'scan_step=next_index' in ui
    assert "'open-pair-check-auto-camera'" in ui
    assert 'auto_start=auto_start_camera' in ui

    decode=scanner.split('if(value){',1)[1].split('return;',1)[0]
    assert 'stopCamera()' not in decode
    assert 'pendingResult={scan_id:scanId,scan_step:scanStep,text:value}' in decode
    assert 'if(args.scan_round!==scanRound)lastDeliveredText=null' in scanner
    assert 'if(opening||stream&&!stopped)return' in scanner
    assert scanner.count('navigator.mediaDevices.getUserMedia(')==1
    assert "if(args.auto_start===true&&!autoStartConsumed){autoStartConsumed=true;startCamera()}" in scanner
