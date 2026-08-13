from content_os.learning.learning_engine import classify

r0=classify(0,'OK')
assert r0.confidence_state=='INTEGRITY_FAIL'
assert r0.eligible is False
assert r0.reason=='sample_required'
assert classify(1,'OK').confidence_state=='INSUFFICIENT_DATA'
assert classify(8,'OK').confidence_state=='INSUFFICIENT_DATA'
print('PASS 5/5')
