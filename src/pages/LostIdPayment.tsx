import { useState, useEffect } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { useToast } from "@/hooks/use-toast";
import { CreditCard, Smartphone, CheckCircle, ArrowLeft } from "lucide-react";

interface LocationState {
  applicationNumber: string;
  applicationId: number;
  waitingCardNumber: string;
}

const LostIdPayment = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { toast } = useToast();
  const [paymentMethod, setPaymentMethod] = useState<'cash' | 'mpesa'>('cash');
  const [loading, setLoading] = useState(false);
  
  const state = location.state as LocationState;
  
  useEffect(() => {
    if (!state?.applicationNumber) {
      toast({
        title: "Error",
        description: "Missing application data. Please restart the process.",
        variant: "destructive"
      });
      navigate('/officer/lost-id');
    }
  }, [state, navigate, toast]);

  const renewalFee = 1000; // KES 1000 renewal fee

  const handlePayment = async () => {
    if (!state) return;

    try {
      setLoading(true);
      
      const paymentData = {
        application_id: state.applicationId,
        amount: renewalFee,
        payment_method: paymentMethod,
        status: 'pending' // Will be marked as completed after admin approval
      };

      const response = await fetch('http://localhost:5000/api/payments', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(paymentData)
      });

      if (response.ok) {
        const data = await response.json();
        
        // Submit application for admin approval
        const submitResponse = await fetch(`http://localhost:5000/api/applications/${state.applicationId}/submit-for-approval`, {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json'
          }
        });

        if (submitResponse.ok) {
          toast({
            title: "Payment Submitted",
            description: `Payment of KES ${renewalFee} via ${paymentMethod.toUpperCase()} submitted successfully`
          });
          
          navigate('/officer/lost-id/confirmation', { 
            state: { 
              ...state,
              paymentId: data.paymentId,
              paymentMethod,
              amount: renewalFee
            } 
          });
        } else {
          throw new Error('Failed to submit application for approval');
        }
      } else {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Payment processing failed');
      }
    } catch (error) {
      toast({
        title: "Payment Error",
        description: error instanceof Error ? error.message : "Payment processing failed",
        variant: "destructive"
      });
    } finally {
      setLoading(false);
    }
  };

  if (!state) {
    return <div>Loading...</div>;
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-background via-background to-primary/5">
      <div className="container mx-auto px-4 py-8">
        {/* Header */}
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-3xl font-bold text-foreground">Payment for Lost ID Replacement</h1>
            <p className="text-muted-foreground">Complete payment to process your application</p>
          </div>
          <Button variant="outline" onClick={() => navigate('/officer/lost-id')}>
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back
          </Button>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Application Summary */}
          <div className="lg:col-span-2">
            <Card className="mb-6">
              <CardHeader>
                <CardTitle>Application Summary</CardTitle>
                <CardDescription>Review your lost ID replacement application details</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <Label>Application Number</Label>
                    <p className="font-medium">{state.applicationNumber}</p>
                  </div>
                  <div>
                    <Label>Waiting Card Number</Label>
                    <p className="font-medium">{state.waitingCardNumber}</p>
                  </div>
                  <div>
                    <Label>Application Type</Label>
                    <Badge variant="secondary">Lost ID Replacement</Badge>
                  </div>
                  <div>
                    <Label>Status</Label>
                    <Badge variant="outline">Pending Payment</Badge>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Payment Method Selection */}
            <Card>
              <CardHeader>
                <CardTitle>Select Payment Method</CardTitle>
                <CardDescription>Choose how you want to pay the renewal fee</CardDescription>
              </CardHeader>
              <CardContent>
                <RadioGroup value={paymentMethod} onValueChange={(value) => setPaymentMethod(value as 'cash' | 'mpesa')}>
                  <div className="space-y-4">
                    {/* Cash Payment */}
                    <div className="flex items-center space-x-2 p-4 border rounded-lg hover:bg-muted/50 transition-colors">
                      <RadioGroupItem value="cash" id="cash" />
                      <Label htmlFor="cash" className="flex items-center gap-3 cursor-pointer flex-1">
                        <CreditCard className="h-5 w-5 text-green-600" />
                        <div>
                          <p className="font-medium">Cash Payment</p>
                          <p className="text-sm text-muted-foreground">Pay directly at the station</p>
                        </div>
                      </Label>
                    </div>

                    {/* M-Pesa Payment */}
                    <div className="flex items-center space-x-2 p-4 border rounded-lg hover:bg-muted/50 transition-colors">
                      <RadioGroupItem value="mpesa" id="mpesa" />
                      <Label htmlFor="mpesa" className="flex items-center gap-3 cursor-pointer flex-1">
                        <Smartphone className="h-5 w-5 text-blue-600" />
                        <div>
                          <p className="font-medium">M-Pesa Payment</p>
                          <p className="text-sm text-muted-foreground">Mobile money payment</p>
                        </div>
                      </Label>
                    </div>
                  </div>
                </RadioGroup>

                {paymentMethod === 'mpesa' && (
                  <div className="mt-4 p-4 bg-blue-50 dark:bg-blue-950/30 rounded-lg">
                    <p className="text-sm text-blue-700 dark:text-blue-300">
                      <strong>Note:</strong> M-Pesa STK push is not configured yet. 
                      Your payment will be marked as pending and will require manual verification by admin.
                    </p>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Payment Summary */}
          <div>
            <Card className="sticky top-8">
              <CardHeader>
                <CardTitle>Payment Summary</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <div className="flex justify-between">
                    <span>Renewal Fee</span>
                    <span>KES {renewalFee.toLocaleString()}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Processing Fee</span>
                    <span>KES 0</span>
                  </div>
                  <hr />
                  <div className="flex justify-between font-bold text-lg">
                    <span>Total</span>
                    <span>KES {renewalFee.toLocaleString()}</span>
                  </div>
                </div>

                <Button 
                  onClick={handlePayment}
                  disabled={loading}
                  className="w-full"
                  size="lg"
                >
                  <CheckCircle className="h-4 w-4 mr-2" />
                  {loading ? "Processing..." : `Pay KES ${renewalFee.toLocaleString()}`}
                </Button>

                <div className="text-xs text-muted-foreground space-y-1">
                  <p>• Payment will be verified by admin</p>
                  <p>• Processing time: 3-5 business days</p>
                  <p>• You will receive SMS notifications</p>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
};

export default LostIdPayment;