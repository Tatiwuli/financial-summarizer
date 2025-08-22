import React from "react"
import { TouchableOpacity, Text, StyleSheet, ViewStyle } from "react-native"

interface ToggleButtonprops {
  label: string
  isActive: boolean
  onPress: () => void
  style?: ViewStyle
  disabled?: boolean
}

export const ToggleButton: React.FC<ToggleButtonprops> = ({
  label,
  isActive,
  onPress,
  style,
  disabled,
}) => {
  return (
    <TouchableOpacity
      style={
        [
          styles.button,
          isActive ? styles.activeButton : styles.inactiveButton,
          disabled ? styles.disabledButton : undefined,
          style,
        ] //last style eh opcao opcional caso quiser customizar o estilo para um btn especifico
      }
      onPress={onPress}
      disabled={disabled}
      activeOpacity={disabled ? 1 : 0.7}
    >
      <Text
        style={[
          styles.text,
          isActive ? styles.activeText : styles.inactiveText,
          disabled ? styles.disabledText : undefined,
        ]}
      >
        {label} {/* show label on the button */}
      </Text>
    </TouchableOpacity>
  )
}

const styles = StyleSheet.create({
  button: {
    paddingVertical: 10,
    paddingHorizontal: 20,
    borderRadius: 8,
    borderWidth: 1,
    alignItems: "center",
    justifyContent: "center",
    minWidth: 120,
  },
  activeButton: {
    backgroundColor: "#007AFF",
    borderColor: "#007AFF",
  },
  inactiveButton: {
    backgroundColor: "#F2F2F7",
    borderColor: "#E5E5EA",
  },
  disabledButton: {
    backgroundColor: "#EDEDED",
    borderColor: "#E5E5EA",
  },
  text: {
    fontSize: 16,
    fontWeight: "400",
  },
  activeText: {
    color: "rgb(0, 0, 0)",
  },
  inactiveText: {
    color: "rgb(0, 0, 0)",
  },
  disabledText: {
    color: "#A0A0A0",
  },
})
