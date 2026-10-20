from rest_framework import serializers

from .models import StandardCategory, TechnicalStandard


class StandardCategorySerializer(serializers.ModelSerializer):
    standards_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = StandardCategory
        fields = ['id', 'title', 'order', 'standards_count']


class TechnicalStandardSerializer(serializers.ModelSerializer):
    category_title = serializers.CharField(source='category.title', read_only=True, default=None)
    file_size = serializers.IntegerField(read_only=True)

    class Meta:
        model = TechnicalStandard
        fields = [
            'id', 'title', 'code', 'category', 'category_title', 'level', 'hours', 'description',
            'pdf', 'file_size', 'downloads', 'created_at', 'updated_at',
        ]
        read_only_fields = ['downloads', 'created_at', 'updated_at']


class AdminTechnicalStandardSerializer(TechnicalStandardSerializer):
    class Meta(TechnicalStandardSerializer.Meta):
        fields = TechnicalStandardSerializer.Meta.fields + ['is_published', 'order']
