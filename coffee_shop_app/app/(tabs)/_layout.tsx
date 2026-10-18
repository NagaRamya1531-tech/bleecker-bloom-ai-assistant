import React from 'react'
import {Tabs} from 'expo-router'
import Entypo from '@expo/vector-icons/Entypo';
import { FontAwesome6 } from '@expo/vector-icons';

const TabsLayout = () => {
  return (
    <>
      <Tabs
        screenOptions={{
          tabBarActiveTintColor: '#C9644B',
          tabBarInactiveTintColor: '#68746B',
          tabBarStyle: { backgroundColor: '#F5F3E9', borderTopColor: '#DEDCCF' },
          tabBarLabelStyle: { fontFamily: 'Sora-SemiBold', fontSize: 11 },
        }}
      >
        <Tabs.Screen 
          name='home'
          options={{
            headerShown: false,
            title: 'Shop',
            tabBarIcon: ({color}) => (
              <Entypo name="home" size={24} color={color} />
            )
          }}
        />

        <Tabs.Screen 
          name='chatRoom'
          options={{
            headerShown: true,
            tabBarStyle: { display: 'none' },
            title: 'Ask',
            tabBarIcon: ({color }) => (
              <FontAwesome6 name="robot" size={24} color={color} />
            )
          }}
        />

    <Tabs.Screen 
          name='order'
          options={{
            headerShown: true,
            tabBarStyle: { display: 'none' },
            title: 'Bag',
            tabBarIcon: ({color}) => (
              <Entypo name="shopping-cart" size={24} color={color} />
            )
          }}
        />
      </Tabs>
    </>
  )
}

export default TabsLayout