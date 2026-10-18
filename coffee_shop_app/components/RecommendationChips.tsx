import { Pressable, Text, View } from 'react-native'
import React from 'react'
import { Recommendation } from '@/types/types';

interface RecommendationChipsProps {
    recommendations?: Recommendation[];
    onAdd?: (message: string) => void;
}

// Tappable suggestions under a bot reply. Tapping sends a chat message so the
// order-taking agent stays the single source of truth for the cart.
const RecommendationChips = ({recommendations, onAdd}: RecommendationChipsProps) => {
  if (!recommendations?.length || !onAdd) return null;

  return (
    <View className="flex-row flex-wrap gap-2 mt-2">
      {recommendations.map((recommendation) => (
        <Pressable
          key={recommendation.name}
          onPress={() => onAdd(`Add one ${recommendation.name} to my order`)}
          className="rounded-full border border-app_orange_color bg-white px-3 py-1"
        >
          <Text className="text-app_orange_color text-[11px] font-[Sora-SemiBold]">
            + {recommendation.name} · ${recommendation.price.toFixed(2)}
          </Text>
        </Pressable>
      ))}
    </View>
  )
}

export default RecommendationChips
