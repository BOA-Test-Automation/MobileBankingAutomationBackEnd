# class SaveBatchTestResultsView(APIView):

#     permission_classes = [IsAuthenticated, IsTester]

#     def post(self, request):
#         try:
#             batch_id = request.data.get('batch_id')
#             overall_status = request.data.get('overall_status')
#             batch_result_data = request.data.get('test_case_results', [])
#             # completed_at = request.data.get('completed_at')

#             if not all([batch_id, overall_status, batch_result_data]):
#                 return Response(
#                     {"error": "Required fields are missing"},
#                     status=status.HTTP_400_BAD_REQUEST
#                 )

#             batch_assignment = get_object_or_404(BatchAssignment, id=batch_id)
            
#             # Update batch status and counters
#             passed_count = sum(1 for tc in batch_result_data if tc['status'] == 'passed')
#             batch_assignment.status = overall_status
#             batch_assignment.completedtestcases = len(batch_result_data)
#             batch_assignment.passedtestcases = passed_count

#             # if completed_at:
#             #     try:
#             #         batch_assignment.completed_at = parse_datetime(completed_at)
#             #     except (ValueError, TypeError):
#             #         pass
#             batch_assignment.save()

#             results = []
#             for tc_result in batch_result_data:

#                 # test_execution = TestExecution.objects.select_related(
#                 #         'test_case', 'executed_by', 'executed_device'
#                 #     ).get(
#                 #         id=tc_result.get('test_execution_id'),
#                 #         batch=batch_assignment
#                 #     )
                
#                 test_execution = get_object_or_404(
#                     TestExecution, 
#                     id=tc_result.get('test_execution_id'),
#                     batch=batch_assignment
#                 )
                
#                 # Update execution status
#                 test_execution.overallstatus = tc_result.get('status')
#                 test_execution.save()

#                 # Save step results
#                 step_results = []
#                 for step_data in tc_result.get('step_results', []):
#                     test_step = get_object_or_404(TestStepTest, id=step_data.get('test_step_id'))

#                     time_start = parse_datetime(step_data.get('time_start'))
#                     time_end = parse_datetime(step_data.get('time_end'))
                    
#                     step_result, created = StepResult.objects.create(
#                         test_execution=test_execution,
#                         test_step=test_step,
#                         defaults={
#                             'actual_id': step_data.get('actual_id'),
#                             'actual_input': step_data.get('actual_input'),
#                             'status': step_data.get('status'),
#                             'duration': step_data.get('duration'),
#                             'time_start': time_start,
#                             'time_end':time_end,
#                             'log_message': step_data.get('log_message'),
#                             'error': step_data.get('error'),
#                         }
#                     )
#                     step_results.append({
#                         "test_step_id": test_step.id,
#                         "status": step_result.status,
#                         "created": created
#                     })

#                 results.append({
#                     "test_case_id": test_execution.test_case.id,
#                     "test_execution_id": test_execution.id,
#                     "step_results": step_results
#                 })

#             return Response({
#                 "message": "Batch test results saved successfully",
#                 "batch_id": batch_assignment.id,
#                 "overall_status": batch_assignment.status,
#                 "passed_count": batch_assignment.passedtestcases,
#                 "total_count": batch_assignment.completedtestcases,
#                 "results": results
#             }, status=status.HTTP_200_OK)

#         except Exception as e:
#             return Response(
#                 {"error": str(e)},
#                 status=status.HTTP_500_INTERNAL_SERVER_ERROR
#             )