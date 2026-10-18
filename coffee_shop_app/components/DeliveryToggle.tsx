import React from 'react';
import { View, Text, TouchableOpacity } from 'react-native';

interface DeliveryToggleProps {
  isDelivery: boolean;
  onChange: (isDelivery: boolean) => void;
}

const DeliveryToggle: React.FC<DeliveryToggleProps> = ({ isDelivery, onChange }) => {

  return (
    <View className="flex-row justify-between bg-[#EDEDED] mx-7 p-1 rounded-xl mt-7">
      <TouchableOpacity
        className={`py-1 px-[15%] font-[Sora-SemiBold] rounded-xl ${isDelivery ? 'bg-app_ink' : ''}`}
        onPress={() => onChange(true)}
      >
        <Text className={`text-lg ${isDelivery ? 'text-white' : 'text-black'}`}>
          Delivery
        </Text>
      </TouchableOpacity>

      <TouchableOpacity
        className={`py-1 px-[15%] font-[Sora-SemiBold] rounded-xl ${!isDelivery ? 'bg-app_ink' : ''}`}
        onPress={() => onChange(false)}
      >
        <Text className={`text-lg ${!isDelivery ? 'text-white' : 'text-black'}`}>
          Pickup
        </Text>
      </TouchableOpacity>
    </View>
  );
};

export default DeliveryToggle;