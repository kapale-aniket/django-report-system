from rest_framework import serializers


class SuggestReplySerializer(serializers.Serializer):
    question_id = serializers.IntegerField(min_value=1)
    question_type = serializers.ChoiceField(choices=['user', 'visitor'], default='user')


class ReportAISuggestionsSerializer(serializers.Serializer):
    report_id = serializers.IntegerField()
    processing_status = serializers.CharField()
    summary = serializers.CharField(allow_blank=True)
    suggested_criterion_scores = serializers.DictField(child=serializers.IntegerField(), required=False)
    suggested_feedback = serializers.CharField(allow_blank=True)
    suggested_teacher_marks = serializers.IntegerField(required=False, allow_null=True)
    provider = serializers.CharField(allow_blank=True)
    ocr_verification = serializers.DictField(required=False)
    extracted_text_preview = serializers.CharField(allow_blank=True, required=False)
    rubric_criteria = serializers.ListField(required=False)
