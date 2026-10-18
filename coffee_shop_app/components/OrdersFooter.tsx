import React from 'react';
import { View, Text } from 'react-native';

interface OrdersFooterProps {
    totalPrice: number;
}

const OrdersFooter: React.FC<OrdersFooterProps> = ({ totalPrice }) => {
    return (
        <>
            <View className='border-b-4 border-[#F9F2ED] mt-3' />
            <Text className="mx-7 text-app_ink text-lg font-[Sora-SemiBold] mb-4 mt-4">
                Order summary
            </Text>

            <View className='flex-row justify-between mx-7 mb-3'>
                <Text className='text-base text-[#59635A] font-[Sora-Regular]'>
                    Items subtotal
                </Text>
                <Text className='text-base text-app_ink font-[Sora-SemiBold]'>
                    $ {totalPrice.toFixed(2)}
                </Text>
            </View>
            <View className='pb-5' />
        </>
    );
};

export default OrdersFooter;