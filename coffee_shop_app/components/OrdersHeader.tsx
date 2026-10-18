import { Text, View } from 'react-native'
import DeliveryToggle from './DeliveryToggle'
import React from 'react'

interface OrdersHeaderProps {
  isDelivery: boolean;
  onDeliveryChange: (isDelivery: boolean) => void;
}

const OrdersHeader = ({ isDelivery, onDeliveryChange }: OrdersHeaderProps) => {
  return (
    <View>
        <DeliveryToggle isDelivery={isDelivery} onChange={onDeliveryChange} />

        <Text
        className="mx-7 mt-7 text-app_ink text-lg font-[Sora-SemiBold]"
        >
        {isDelivery ? 'Neighborhood delivery' : 'Pickup location'}
        </Text>
        <Text
        className="mx-7 mt-3 text-app_ink text-base font-[Sora-SemiBold] mb-2"
        >
        {isDelivery ? 'Greenwich Village' : 'Bleecker & Bloom'}
        </Text>
        <Text
        className="mx-7 text-[#6E7469] text-xs font-[Sora-Regular] mb-3"
        >
        {isDelivery
          ? 'We deliver to SoHo, West Village, and Lower Manhattan too.'
          : 'Visit us in Greenwich Village, New York City.'}
        </Text>

        <View className="mx-12 border-b border-gray-400 my-4 " />
    </View>
  )
}

export default OrdersHeader