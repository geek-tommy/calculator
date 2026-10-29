#if COMMUNITY_MACCATALYST
using System;
using System.IO;
using System.Linq;
using System.Runtime.CompilerServices;
using CalculatorApp.Controls;
using Windows.UI.Core;
using Windows.UI.Xaml;
using Windows.UI.Xaml.Controls;
using Windows.UI.Xaml.Controls.Primitives;
using Windows.UI.Xaml.Input;
using Windows.UI.Xaml.Media;

namespace CalculatorApp.Common
{
    internal static class MacCatalystInteractionFeedback
    {
        private static readonly ConditionalWeakTable<Control, object> Attached = new ConditionalWeakTable<Control, object>();

        public static void Attach(Control control)
        {
            if (Attached.TryGetValue(control, out _)) return;
            Attached.Add(control, new object());

            // Catalyst can synthesize touch entry without a matching mouse exit.
            // Run after the control has finished processing release/capture changes.
            var released = new PointerEventHandler((sender, args) => QueueReset(control));
            control.AddHandler(UIElement.PointerReleasedEvent, released, true);
            control.AddHandler(UIElement.PointerCanceledEvent, released, true);
            control.AddHandler(UIElement.PointerCaptureLostEvent, released, true);
            control.PointerExited += released;
            control.LostFocus += (sender, args) => QueueReset(control);
            control.KeyUp += (sender, args) => QueueReset(control);
            if (control is ButtonBase button)
                button.Click += (sender, args) => QueueReset(control);
        }

        public static void AttachTree(DependencyObject root)
        {
            if (root is Button || root is NavigationViewItem) Attach((Control)root);
            for (int i = 0; i < VisualTreeHelper.GetChildrenCount(root); i++)
                AttachTree(VisualTreeHelper.GetChild(root, i));
        }

        private static void QueueReset(Control control)
        {
            _ = control.Dispatcher.RunAsync(CoreDispatcherPriority.Low, () => Reset(control));
        }

        private static void Reset(Control control)
        {
            if (!control.IsEnabled || (control is ButtonBase button && button.IsPressed)) return;
            // Selection and keyboard focus are separate from transient hover/press feedback.
            string state = control is NavigationViewItem item && item.IsSelected ? "Selected" : "Normal";
            VisualStateManager.GoToState(control, state, false);
        }

        public static void VerifyOnStartup(DependencyObject root)
        {
            string proof = Environment.GetEnvironmentVariable("UNO_CALCULATOR_INTERACTION_PROOF");
            if (string.IsNullOrEmpty(proof)) return;
            _ = Windows.UI.Xaml.Window.Current.Dispatcher.RunAsync(CoreDispatcherPriority.Low, () =>
            {
                try
                {
                    var button = FindButton(root) ?? throw new InvalidOperationException("No calculator button found");
                    button.ApplyTemplate();
                    var templateRoot = (FrameworkElement)VisualTreeHelper.GetChild(button, 0);
                    var states = VisualStateManager.GetVisualStateGroups(templateRoot).First(group => group.Name == "CommonStates");
                    foreach (string state in new[] { "Pressed", "PointerOver" })
                    {
                        if (!VisualStateManager.GoToState(button, state, false))
                            throw new InvalidOperationException("Cannot enter " + state);
                        Reset(button);
                        if (states.CurrentState?.Name != "Normal")
                            throw new InvalidOperationException(state + " did not reset to Normal");
                        if (templateRoot is Panel panel && panel.Background is SolidColorBrush actual &&
                            button.Background is SolidColorBrush expected && actual.Color != expected.Color)
                            throw new InvalidOperationException(state + " background did not recover");
                    }
                    File.WriteAllText(proof, "PASS: pressed and hover states return to Normal");
                }
                catch (Exception error)
                {
                    File.WriteAllText(proof, "FAIL: " + error.Message);
                }
            });
        }

        private static CalculatorButton FindButton(DependencyObject root)
        {
            if (root is CalculatorButton button && button.IsEnabled) return button;
            for (int i = 0; i < VisualTreeHelper.GetChildrenCount(root); i++)
            {
                var found = FindButton(VisualTreeHelper.GetChild(root, i));
                if (found != null) return found;
            }
            return null;
        }
    }
}
#endif
