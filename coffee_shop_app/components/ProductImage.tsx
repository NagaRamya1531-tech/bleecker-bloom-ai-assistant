import { Image, ImageStyle, StyleProp, View } from 'react-native'
import React from 'react'
import Feather from '@expo/vector-icons/Feather';

interface ProductImageProps {
    uri?: string;
    className?: string;
    style?: StyleProp<ImageStyle>;
    accessibilityLabel?: string;
    iconSize?: number;
}

// Product photo, or a neutral placeholder for menu items that don't have a photo yet.
const ProductImage = ({uri, className, style, accessibilityLabel, iconSize = 28}: ProductImageProps) => {
  if (uri) {
    return (
      <Image
        source={{ uri }}
        resizeMode="cover"
        accessibilityLabel={accessibilityLabel}
        className={className}
        style={style}
      />
    )
  }

  return (
    <View
      accessibilityLabel={accessibilityLabel}
      className={`${className ?? ''} items-center justify-center bg-app_cream`}
      style={style}
    >
      <Feather name="coffee" size={iconSize} color="#A9B98B" />
    </View>
  )
}

export default ProductImage
